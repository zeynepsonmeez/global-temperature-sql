"""The README's "Findings" table, checked against the database.

Every claim in the README is computed by a query in sql/. If the data is refreshed and a
finding changes, these tests fail until the README is updated — the text cannot drift away
from the data. (Values refer to the committed NASA snapshot of 10 Nov 2026.)
"""

import pytest

from library import load_samples

SAMPLES = {s.code: s.sql for s in load_samples()}


@pytest.fixture(scope="module")
def run(admin_conn):
    def query(code: str) -> list[tuple]:
        try:
            with admin_conn.cursor() as cur:
                cur.execute(SAMPLES[code])
                return cur.fetchall()
        finally:
            admin_conn.rollback()            # a failing query must not poison the shared connection

    return query


def test_hottest_years_are_all_recent(run):
    rows = run("B2")                                   # (year, annual_anomaly), top 10
    assert rows[0][0] == 2024 and float(rows[0][1]) == pytest.approx(1.28)
    assert all(year >= 2015 for year, _ in rows)


def test_no_month_below_the_baseline_since_september_1992(run):
    last_cool, _ = run("B8")[0]
    assert str(last_cool) == "1992-09-01"


def test_longest_streak_above_one_degree(run):
    start, end, months = run("A10")[0]
    assert (start, months) == ("Jun 2023", 41)


def test_warming_rate_since_1970(run):
    rates = {region: float(r1970) for region, _, r1970, _ in run("A6")}
    assert rates["GLB"] == pytest.approx(0.20, abs=0.005)


def test_arctic_warms_three_times_faster(run):
    bands = {region: float(ratio) for region, _, ratio in run("A7")}
    assert bands["64N-90N"] == pytest.approx(3.0, abs=0.05)


def test_hemisphere_gap_widened(run):
    gaps = {int(decade): float(gap) for decade, _, _, gap in run("I2")}
    assert gaps[1990] == pytest.approx(0.06, abs=0.005)
    assert gaps[2020] == pytest.approx(0.61, abs=0.005)


def test_2016_drops_when_enso_is_removed(run):
    ranks = {year: (observed, adjusted) for year, *_, observed, adjusted in run("D8")}
    if not ranks:
        pytest.skip("models not run")
    assert ranks[2016] == (4, 9)
    assert {year for year, (_, adjusted) in ranks.items() if adjusted <= 3} == {2023, 2024, 2025}


def test_warming_accelerated_around_1975(run):
    rows = run("D9")
    if not rows:
        pytest.skip("models not run")
    best_year, _, before, after = rows[0]
    assert best_year == 1975
    assert float(after) > 5 * float(before)


def test_land_warms_twice_as_fast_as_ocean(grid_cur, run):     # grid_cur: skips without the grid
    rates = {surface: float(rate) for surface, _, rate in run("S6")}
    if not rates:
        pytest.skip("full grid not loaded (CI loads a subset)")
    assert rates["land"] / rates["ocean"] == pytest.approx(2.0, abs=0.1)
