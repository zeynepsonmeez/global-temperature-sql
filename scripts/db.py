"""Shared database connection helper. Settings come from .env (see .env.example)."""

from __future__ import annotations

import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def connection_settings() -> dict[str, str]:
    missing = [k for k in ("POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD") if not os.getenv(k)]
    if missing:
        raise RuntimeError(f"Missing settings in .env: {', '.join(missing)} (copy .env.example to .env)")
    return {
        "dbname": os.environ["POSTGRES_DB"],
        "user": os.environ["POSTGRES_USER"],
        "password": os.environ["POSTGRES_PASSWORD"],
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": os.getenv("POSTGRES_PORT", "5433"),
    }


def get_connection(**overrides) -> psycopg.Connection:
    return psycopg.connect(**{**connection_settings(), **overrides}, connect_timeout=5)
