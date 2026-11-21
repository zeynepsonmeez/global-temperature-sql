"""Challenge checker tests: every reference query must run and must accept itself."""

import pandas as pd
import pytest

from challenges import CHALLENGES, compare
from database import database_available, run_user_query
from sql_guard import check_query

needs_db = pytest.mark.skipif(not database_available(), reason="database not available")


@pytest.mark.parametrize("challenge", CHALLENGES, ids=lambda c: c.id)
def test_reference_passes_the_guard(challenge):
    assert check_query(challenge.reference_sql).ok


@needs_db
@pytest.mark.parametrize("challenge", CHALLENGES, ids=lambda c: c.id)
def test_reference_accepts_itself(challenge):
    result = run_user_query(challenge.reference_sql)
    assert result.error is None, result.error
    assert not result.frame.empty
    correct, _, _ = compare(result.frame, result.frame, challenge.ordered)
    assert correct


def test_compare_ignores_column_names_and_row_order():
    reference = pd.DataFrame({"year": [2024, 2023], "anomaly": [1.28, 1.17]})
    user = pd.DataFrame({"y": [2023, 2024], "a": [1.1712, 1.2799]})   # unrounded, other order
    assert compare(user, reference)[0]


@pytest.mark.parametrize("user, reason", [
    (pd.DataFrame({"year": [2024, 2023]}), "pg.ch.cols"),
    (pd.DataFrame({"year": [2024], "a": [1.28]}), "pg.ch.rows"),
    (pd.DataFrame({"year": [2024, 2022], "a": [1.28, 1.17]}), "pg.ch.values"),
])
def test_compare_explains_wrong_answers(user, reason):
    reference = pd.DataFrame({"year": [2024, 2023], "anomaly": [1.28, 1.17]})
    correct, got_reason, _ = compare(user, reference)
    assert not correct and got_reason == reason


def test_compare_treats_nulls_consistently():
    reference = pd.DataFrame({"year": [1880, 1881], "change": [None, 0.09]})
    user = pd.DataFrame({"year": [1881, 1880], "change": [0.09, float("nan")]})
    assert compare(user, reference)[0]
