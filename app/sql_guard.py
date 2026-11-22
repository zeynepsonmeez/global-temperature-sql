"""Validation for user-submitted SQL in the Playground.

This is the FIRST line of defence: it rejects anything that is not a single read-only
query and explains why in plain language. The SECOND (and authoritative) line is the
database itself — the gts_reader role is read-only, can see only the playground views,
and has a 3-second statement timeout (database/roles.sql).

Checking that a query "starts with SELECT" is not enough:
  * "SELECT 1; DROP TABLE x"         — a second statement after the first
  * "WITH d AS (DELETE ...) SELECT"  — a data-modifying CTE
  * "SELECT * INTO new_table FROM t" — SELECT INTO creates a table
  * "SELECT pg_sleep(60)"            — a harmless-looking denial of service
so the query is parsed into a syntax tree and every node is inspected.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

# sqlglot logs a warning for every statement it cannot model (VACUUM, DO, ...); those are
# rejected anyway, so the warnings would only fill the app's log.
logging.getLogger("sqlglot").setLevel(logging.ERROR)

MAX_QUERY_LENGTH = 5_000

# Statement types that must never appear anywhere in the tree.
FORBIDDEN_NODES: tuple[type[exp.Expression], ...] = (
    exp.Insert, exp.Update, exp.Delete, exp.Merge,
    exp.Create, exp.Drop, exp.Alter, exp.TruncateTable,
    exp.Command,            # anything sqlglot does not model: SET, COPY, GRANT, VACUUM, ...
    exp.Into,               # SELECT ... INTO new_table
    exp.Transaction, exp.Commit, exp.Rollback,
    exp.Lock,
)

# Functions with side effects or that reach outside the database. Most are also
# blocked by PostgreSQL permissions; listing them gives a clear error message.
FORBIDDEN_FUNCTIONS = {
    "pg_sleep", "pg_sleep_for", "pg_sleep_until",
    "pg_read_file", "pg_read_binary_file", "pg_ls_dir", "pg_stat_file",
    "lo_import", "lo_export", "lo_get", "lo_put",
    "set_config", "current_setting",
    "pg_terminate_backend", "pg_cancel_backend", "pg_reload_conf",
    "dblink", "dblink_exec",
    "nextval", "setval",
    "txid_current", "pg_advisory_lock", "pg_advisory_xact_lock",
}


@dataclass(frozen=True)
class GuardResult:
    ok: bool
    message: str = ""


def _reject(message: str) -> GuardResult:
    return GuardResult(ok=False, message=message)


def check_query(sql: str) -> GuardResult:
    """Return ok=True if `sql` is a single read-only query, else a reason."""
    text = (sql or "").strip()
    if not text:
        return _reject("The query is empty.")
    if len(text) > MAX_QUERY_LENGTH:
        return _reject(f"The query is too long (maximum {MAX_QUERY_LENGTH:,} characters).")

    try:
        statements = [s for s in sqlglot.parse(text, read="postgres") if s is not None]
    except ParseError as error:
        first = error.errors[0] if error.errors else {}
        where = f" near line {first.get('line')}" if first.get("line") else ""
        return _reject(f"The query could not be parsed{where}. Check the syntax.")

    if len(statements) != 1:
        return _reject("Only one statement can be run at a time. Remove the extra ';' statements.")

    tree = statements[0]
    if not isinstance(tree, exp.Query):  # Select, Union/Intersect/Except, or a WITH ... SELECT
        return _reject("Only read-only queries (SELECT or WITH ... SELECT) are allowed.")

    for node in tree.walk():
        if isinstance(node, FORBIDDEN_NODES):
            kind = type(node).__name__.upper().replace("COMMAND", "this command")
            return _reject(f"{kind} is not allowed: the Playground is read-only.")
        if isinstance(node, (exp.Anonymous, exp.Func)):
            name = (node.name if isinstance(node, exp.Anonymous) else node.sql_name()).lower()
            if name in FORBIDDEN_FUNCTIONS:
                return _reject(f"The function {name}() is not allowed in the Playground.")

    return GuardResult(ok=True)
