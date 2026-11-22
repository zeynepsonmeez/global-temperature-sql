"""Security tests for the Playground validator (no database needed)."""

from pathlib import Path

import pytest

from sql_guard import check_query

ROOT = Path(__file__).resolve().parent.parent

ALLOWED = [
    "SELECT * FROM v_monthly LIMIT 5",
    "select year, avg(anomaly) from v_monthly group by year",
    "WITH a AS (SELECT 1 AS x) SELECT x FROM a",
    "(SELECT 1) UNION ALL (SELECT 2)",
    "SELECT * FROM v_monthly WHERE region = 'GLB' AND anomaly > 1.0;",   # trailing ; is fine
    "-- a comment\nSELECT 1",
    "SELECT 'DROP TABLE x' AS harmless_text",                            # keyword inside a string
    "SELECT ';' AS semicolon_in_text",                                    # ; inside a string
    "select 1 /* ; drop table regions */",                               # ; inside a comment
    "SELECT 1 -- ; DROP TABLE regions",
    "SELECT * FROM v_monthly WHERE region = $$GLB$$",                    # dollar-quoted string
    "WITH x AS (SELECT 1) SELECT * FROM x UNION SELECT 2",
]

BLOCKED = [
    ("", "empty"),
    ("   ", "empty"),
    ("DROP TABLE regions", "read-only"),
    ("DELETE FROM v_monthly", "read-only"),
    ("UPDATE regions SET name = 'x'", "read-only"),
    ("INSERT INTO regions VALUES (1)", "read-only"),
    ("ALTER TABLE regions ADD COLUMN x int", "read-only"),
    ("TRUNCATE regions", "read-only"),
    ("CREATE TABLE x (a int)", "read-only"),
    ("SELECT 1; DROP TABLE regions", "one statement"),
    ("SELECT 1; SELECT 2", "one statement"),
    ("WITH d AS (DELETE FROM regions RETURNING *) SELECT * FROM d", "not allowed"),
    ("SELECT * INTO copy_table FROM regions", "not allowed"),
    ("SELECT pg_sleep(10)", "pg_sleep"),
    ("SELECT * FROM v_monthly WHERE pg_sleep(1) IS NULL", "pg_sleep"),
    ("SELECT pg_read_file('/etc/passwd')", "pg_read_file"),
    ("SELECT set_config('statement_timeout', '0', false)", "set_config"),
    ("SET statement_timeout = 0", "read-only"),
    ("SET default_transaction_read_only = off", "read-only"),
    ("COPY regions TO STDOUT", "read-only"),
    ("GRANT ALL ON regions TO public", "read-only"),
    ("BEGIN", "read-only"),
    ("drop table regions", "read-only"),                                  # lower case
    ("SELECT * FROM v_monthly FOR UPDATE", "not allowed"),               # row locks
    ("DO $$ BEGIN DELETE FROM regions; END $$", "read-only"),           # anonymous code block
    ("EXPLAIN ANALYZE DELETE FROM regions", "read-only"),               # EXPLAIN ANALYZE executes
    ("REFRESH MATERIALIZED VIEW mv_grid_annual", "read-only"),
    ("CALL some_procedure()", "read-only"),
    ("VACUUM regions", "read-only"),
    ("LISTEN channel", "read-only"),
    ("PREPARE p AS SELECT 1", "read-only"),
    ("COPY (SELECT 1) TO '/tmp/x'", "read-only"),
    ("INSERT INTO x SELECT 1", "read-only"),
    ("SELECT lo_import('/etc/passwd')", "lo_import"),
    ("SELECT dblink('host=x', 'select 1')", "dblink"),
    ("SELECT current_setting('statement_timeout')", "current_setting"),
    ("SELECT pg_terminate_backend(1)", "pg_terminate_backend"),
    ("SELECT nextval('s')", "nextval"),
    ("SELECT FROM WHERE", "parsed"),
    ("SELECT " + "1," * 3000 + "1", "too long"),
]


@pytest.mark.parametrize("sql", ALLOWED)
def test_allowed_queries(sql):
    result = check_query(sql)
    assert result.ok, result.message


@pytest.mark.parametrize("sql, expected", BLOCKED)
def test_blocked_queries(sql, expected):
    result = check_query(sql)
    assert not result.ok
    assert expected.lower() in result.message.lower()


@pytest.mark.parametrize("name", ["basic", "intermediate", "advanced", "spatial", "drivers"])
def test_every_library_query_passes_the_guard(name):
    """Every sample query in sql/ must be runnable in the Playground."""
    text = (ROOT / "sql" / f"{name}_queries.sql").read_text(encoding="utf-8")
    import sqlglot
    for statement in sqlglot.parse(text, read="postgres"):
        if statement is not None:
            sql = statement.sql(dialect="postgres")
            assert check_query(sql).ok, sql[:80]
