"""Playground error explanations, triggered with real PostgreSQL errors (read-only role).

These queries bypass the validator on purpose: they reach the database and fail there.
"""

import pytest

from database import database_available, estimate_cost, friendly_error_key, run_user_query
from library import load_samples

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


@pytest.mark.parametrize("sample", load_samples(), ids=lambda s: s.code)
def test_every_library_query_runs_as_the_playground_role(sample):
    """The library tests in test_database.py run as the owner; this runs each query exactly
    as a visitor would — read-only role, its memory and temp-file limits, the cost gate."""
    assert not estimate_cost(sample.sql).too_expensive
    result = run_user_query(sample.sql)
    assert result.error is None, result.error


@pytest.mark.parametrize("sql", [
    "SELECT count(*) FROM v_monthly a, v_monthly b, v_monthly c",
    "SELECT count(*) FROM v_grid a CROSS JOIN v_grid b",
    "SELECT count(*) FROM generate_series(1, 1000000000)",
])
def test_cost_gate_stops_expensive_queries_before_they_run(sql):
    estimate = estimate_cost(sql)
    assert estimate.error is None and estimate.too_expensive


def test_cost_gate_reports_planner_errors_instead_of_raising():
    estimate = estimate_cost("SELECT * FROM no_such_table")
    assert estimate.error is not None and not estimate.too_expensive


def test_server_side_cursor_streams_only_the_rows_it_needs():
    """25 million rows exist; only max_rows + 1 are transferred, so this is fast."""
    result = run_user_query("SELECT * FROM v_grid", max_rows=1000)
    assert result.error is None and len(result.frame) == 1000 and result.truncated
    assert result.elapsed_ms < 2_000


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
