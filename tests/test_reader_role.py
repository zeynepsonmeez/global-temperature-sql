"""Database-level security tests for the read-only role, WITHOUT the app's SQL validator.

These prove the second line of defence: even a query that slipped past app/sql_guard.py
cannot write, cannot see the base tables and cannot run for long.
"""

import psycopg
import pytest

from database import connect, database_available

pytestmark = pytest.mark.skipif(not database_available(), reason="database not available")


def run(sql: str):
    with connect() as conn:
        conn.read_only = False          # simulate an attacker who turned the client flag off
        with conn.cursor() as cur:
            cur.execute(sql)
            return cur.fetchall() if cur.description else None


def test_reader_can_query_playground_views():
    assert run("SELECT count(*) FROM v_monthly")[0][0] > 0


# With conn.read_only = False, psycopg opens transactions with BEGIN READ WRITE, which
# overrides the role's default_transaction_read_only. So "read-only by default" is NOT a
# security boundary on its own — these writes are stopped by missing PRIVILEGES instead.
@pytest.mark.parametrize("sql, error", [
    ("SELECT * FROM public.monthly_anomalies", psycopg.errors.InsufficientPrivilege),
    ("CREATE TABLE playground.x (a int)", psycopg.errors.InsufficientPrivilege),
    ("CREATE TEMP TABLE x (a int)", psycopg.errors.InsufficientPrivilege),
    ("SELECT 1 AS a INTO x", psycopg.errors.InsufficientPrivilege),
    ("DELETE FROM v_monthly", psycopg.errors.ObjectNotInPrerequisiteState),
    ("SELECT pg_read_file('/etc/passwd')", psycopg.errors.InsufficientPrivilege),
    ("COPY (SELECT 1) TO PROGRAM 'id'", psycopg.errors.InsufficientPrivilege),
    ("SELECT pg_sleep(5)", psycopg.errors.QueryCanceled),
])
def test_reader_is_blocked_by_the_database(sql, error):
    with pytest.raises(error):
        run(sql)


def test_turning_read_only_off_still_cannot_create_objects():
    """Even with default_transaction_read_only switched off, there is nowhere to write."""
    with connect() as conn:
        conn.read_only = False
        conn.autocommit = True
        conn.execute("SET default_transaction_read_only = off")
        for sql in ("CREATE TABLE playground.x (a int)",
                    "CREATE TABLE public.x (a int)",
                    "CREATE TEMP TABLE x (a int)"):
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                conn.execute(sql)
