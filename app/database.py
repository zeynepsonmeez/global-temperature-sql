"""Database access for the web app. Every connection uses the READ-ONLY role gts_reader."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import psycopg
import streamlit as st
from dotenv import load_dotenv
from psycopg.types.numeric import FloatLoader

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

MAX_ROWS = 1_000
# Planner cost above which a Playground query is refused before it runs. Calibrated by
# measuring every query in sql/: the most expensive one costs ~0.3M, a cross join of the
# grid ~8.6 trillion. See docs/SECURITY.md.
MAX_PLAN_COST = 2_000_000


def reader_settings() -> dict[str, str]:
    return {
        "dbname": os.getenv("POSTGRES_DB", "global_temperature"),
        "user": os.getenv("POSTGRES_READER_USER", "gts_reader"),
        "password": os.getenv("POSTGRES_READER_PASSWORD", ""),
        "host": os.getenv("POSTGRES_HOST", "127.0.0.1"),
        "port": os.getenv("POSTGRES_PORT", "5433"),
    }


def connect() -> psycopg.Connection:
    conn = psycopg.connect(**reader_settings(), connect_timeout=5)
    conn.read_only = True                                     # every transaction is READ ONLY
    conn.adapters.register_loader("numeric", FloatLoader)     # NUMERIC -> float for pandas/Plotly
    return conn


def database_available() -> bool:
    try:
        with connect() as conn:
            conn.execute("SELECT 1")
        return True
    except psycopg.Error:
        return False


@st.cache_data(ttl=3600, show_spinner=False)
def read_df(sql: str, params: dict | None = None) -> pd.DataFrame:
    """Run one of the app's own (trusted, parameterised) queries and cache the result."""
    with connect() as conn, conn.cursor() as cur:
        # params=None (not {}) when there are no placeholders: psycopg then sends the text
        # as-is, so a '%' inside a comment of a sql/ library query cannot break it.
        cur.execute(sql, params or None)
        columns = [column.name for column in cur.description]
        return pd.DataFrame(cur.fetchall(), columns=columns)


def read_row(sql: str, params: dict | None = None) -> SimpleNamespace:
    """First row as attributes, keeping each column's own type.

    DataFrame.iloc[0] would turn a row of mixed ints and floats into one float Series
    (2025 -> 2025.0); to_dict("records") keeps the per-column dtypes.
    """
    return SimpleNamespace(**read_df(sql, params).to_dict("records")[0])


@dataclass
class QueryResult:
    frame: pd.DataFrame | None = None
    elapsed_ms: float = 0.0
    truncated: bool = False
    error: psycopg.Error | None = None


@dataclass
class CostEstimate:
    total_cost: float = 0.0          # planner cost units of the whole query
    plan_rows: int = 0               # rows the planner expects to return
    top_node: str = ""               # e.g. "Nested Loop", "Seq Scan"
    error: psycopg.Error | None = None

    @property
    def too_expensive(self) -> bool:
        return self.error is None and self.total_cost > MAX_PLAN_COST


def _statement(sql: str) -> str:
    """The query text without trailing semicolons, so it can be embedded in EXPLAIN / DECLARE."""
    return sql.strip().rstrip(";").strip()


def estimate_cost(sql: str) -> CostEstimate:
    """Ask the planner what a query would cost — EXPLAIN plans it without running it.

    The third layer of the Playground's defence: a cross join of two 25M-row tables is
    stopped here before it uses any CPU, instead of after 3 seconds by the timeout.
    """
    try:
        with connect() as conn, conn.cursor() as cur:
            cur.execute("EXPLAIN (FORMAT JSON) " + _statement(sql))
            plan = cur.fetchone()[0][0]["Plan"]
    except psycopg.Error as error:
        return CostEstimate(error=error)
    return CostEstimate(total_cost=float(plan["Total Cost"]), plan_rows=int(plan["Plan Rows"]),
                        top_node=plan["Node Type"])


def run_user_query(sql: str, max_rows: int = MAX_ROWS) -> QueryResult:
    """Run a Playground query (already checked by sql_guard) with a row limit.

    The limit is applied with fetchmany(), not by editing the user's SQL: rewriting the
    text could change its meaning. The cursor is a SERVER-SIDE (named) cursor: PostgreSQL
    sends only the rows that are fetched. A normal client-side cursor would transfer the
    whole result first — all 25 million rows of "SELECT * FROM v_grid" — and only then let
    fetchmany() discard them.
    """
    started = time.perf_counter()
    try:
        with connect() as conn, conn.cursor(name="playground") as cur:
            cur.execute(_statement(sql))
            columns = [column.name for column in cur.description] if cur.description else []
            rows = cur.fetchmany(max_rows + 1) if columns else []
    except psycopg.Error as error:
        return QueryResult(error=error, elapsed_ms=(time.perf_counter() - started) * 1000)

    truncated = len(rows) > max_rows
    frame = pd.DataFrame(rows[:max_rows], columns=columns)
    return QueryResult(frame=frame, elapsed_ms=(time.perf_counter() - started) * 1000, truncated=truncated)


def friendly_error_key(error: psycopg.Error) -> str:
    """Map a PostgreSQL error to an i18n key with a beginner-friendly explanation."""
    errors = psycopg.errors
    if isinstance(error, errors.QueryCanceled):
        return "err.timeout"
    if isinstance(error, errors.InsufficientPrivilege):
        return "err.permission"
    if isinstance(error, errors.ReadOnlySqlTransaction):
        return "err.readonly"
    if isinstance(error, errors.UndefinedTable):
        return "err.undefined_table"
    if isinstance(error, errors.UndefinedColumn):
        return "err.undefined_column"
    if isinstance(error, errors.GroupingError):
        return "err.group_by"
    if isinstance(error, errors.SyntaxError):
        return "err.syntax"
    return "err.other"
