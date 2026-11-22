"""Shared database fixtures.

The database tests need the Docker database running and loaded:

    docker compose up -d
    python scripts/load_data.py
    pytest

If it is not reachable, every test that asks for a database fixture is skipped and the
file-only tests still run. Tests that need a particular load step (grid, models) skip
with a hint naming the script to run.
"""

import psycopg
import pytest

from db import get_connection


@pytest.fixture(scope="session")
def admin_conn():
    """One owner connection for the whole run, with PostGIS on the search path."""
    try:
        connection = get_connection()
    except (psycopg.OperationalError, RuntimeError) as error:
        pytest.skip(f"database not available: {error}")
    with connection.cursor() as cursor:
        cursor.execute("SET search_path = public, postgis")
    connection.commit()
    yield connection
    connection.close()


@pytest.fixture
def admin_cur(admin_conn):
    """Each test runs inside a transaction that is rolled back afterwards."""
    with admin_conn.cursor() as cursor:
        yield cursor
    admin_conn.rollback()


def _require(cur, check_sql: str, hint: str) -> None:
    """Skip the test unless check_sql returns true; hint says which load step is missing."""
    cur.execute(check_sql)
    if not cur.fetchone()[0]:
        pytest.skip(hint)


@pytest.fixture
def grid_cur(admin_cur):
    _require(admin_cur, "SELECT to_regclass('grid_anomalies') IS NOT NULL AND EXISTS (SELECT 1 FROM grid_cells)",
             "grid not loaded (run scripts/load_grid.py)")
    return admin_cur
