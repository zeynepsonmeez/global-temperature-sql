"""Playground error explanations, triggered with real PostgreSQL errors (read-only role).

These queries bypass the validator on purpose: they reach the database and fail there.
"""

import pytest

from database import database_available, friendly_error_key, run_user_query

pytestmark = pytest.mark.skipif(not database_available(), reason="database not available")


@pytest.mark.parametrize("sql, key", [
    ("SELECT * FROM no_such_table", "err.undefined_table"),
    ("SELECT no_such_column FROM v_monthly", "err.undefined_column"),
    ("SELECT year, AVG(anomaly) FROM v_monthly", "err.group_by"),
    ("SELECT * FROM public.monthly_anomalies", "err.permission"),
    ("SELEC 1", "err.syntax"),
    ("SELECT 1 / 0", "err.other"),
])
def test_database_errors_get_a_plain_explanation(sql, key):
    result = run_user_query(sql)
    assert result.error is not None and result.frame is None
    assert friendly_error_key(result.error) == key


def test_long_query_is_cancelled_by_the_role_timeout():
    result = run_user_query("SELECT pg_sleep(5)")                    # role limit: 3 seconds
    assert friendly_error_key(result.error) == "err.timeout"
    assert 2_500 < result.elapsed_ms < 4_500


def test_row_limit_is_applied_without_rewriting_the_query():
    result = run_user_query("SELECT * FROM v_monthly", max_rows=10)
    assert result.error is None
    assert len(result.frame) == 10 and result.truncated


def test_small_result_is_not_marked_truncated():
    result = run_user_query("SELECT region FROM v_monthly GROUP BY region", max_rows=10)
    assert len(result.frame) == 3 and not result.truncated
