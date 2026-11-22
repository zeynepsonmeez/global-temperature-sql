"""Tests for the ENSO / CO2 loader (files only) and the statistical model outputs (database)."""

import pandas as pd
import psycopg
import pytest

import load_drivers as ld
from db import get_connection
from library import load_samples

# --- Loader: parsing and validation (no database) ----------------------------------------

@pytest.fixture(scope="module")
def oni():
    return ld.read_oni()


@pytest.fixture(scope="module")
def co2():
    return ld.read_co2()


def test_oni_seasons_are_stored_on_their_centre_month(oni):
    first = oni.iloc[0]
    assert (first.season, first.obs_date) == ("DJF", pd.Timestamp("1950-01-01"))
    ndj = oni[oni.season == "NDJ"].iloc[0]
    assert ndj.obs_date.month == 12                           # Nov–Dec–Jan -> December


def test_series_are_monthly_without_gaps_or_duplicates(oni, co2):
    ld.validate(oni, co2)                                     # raises on any problem


def test_missing_value_sentinels_become_null(co2):
    assert co2.days_measured.isna().sum() > 0                 # NOAA's -1 values
    assert (co2.days_measured.dropna() >= 0).all()
    assert co2.co2_ppm.between(250, 600).all()                # no -99.99 leaked into the data


def test_validation_catches_a_missing_month(oni, co2):
    with pytest.raises(ValueError, match="missing months"):
        ld.validate(oni.drop(index=100), co2)


# --- Model outputs (database, written by run_models.py) -------------------------------------

@pytest.fixture(scope="module")
def results():
    try:
        conn = get_connection()
    except (psycopg.OperationalError, RuntimeError) as error:
        pytest.skip(f"database not available: {error}")
    with conn, conn.cursor() as cur:
        cur.execute("SELECT to_regclass('model_results') IS NOT NULL")
        if not cur.fetchone()[0]:
            pytest.skip("drivers schema not installed")
        cur.execute("SELECT metric, value, ci_low, ci_high FROM model_results")
        rows = {m: (v, lo, hi) for m, v, lo, hi in cur.fetchall()}
        if not rows:
            pytest.skip("models not run (python scripts/run_models.py)")
        cur.execute("SELECT count(*), max(abs(observed - enso_component - adjusted)) FROM model_enso_adjusted")
        adjusted = cur.fetchone()
        d3 = next(s for s in load_samples() if s.code == "D3")    # the lagged-correlation query
        cur.execute(d3.sql)
        lag_correlations = {lag: corr for lag, corr, _ in cur.fetchall()}
    conn.close()
    return {"metrics": rows, "adjusted": adjusted, "lag_correlations": lag_correlations}


def test_enso_lag_agrees_with_the_sql_lag_correlation(results):
    sql_best = max(results["lag_correlations"], key=results["lag_correlations"].get)
    model_lag = results["metrics"]["enso_lag_months"][0]
    assert abs(model_lag - sql_best) <= 1                     # AIC (1970+) vs correlation (1950+)


def test_enso_effect_is_positive_and_significant(results):
    value, low, high = results["metrics"]["enso_coefficient"]
    assert value > 0 and low > 0                              # El Niño warms the globe


def test_newey_west_intervals_are_wider_than_classical(results):
    """Residuals are autocorrelated, so the classical interval is too narrow."""
    m = results["metrics"]
    assert m["residual_autocorrelation_lag1"][0] > 0.3
    for name in ("monthly", "annual"):
        _, n_low, n_high = m[f"trend_{name}_naive"]
        _, h_low, h_high = m[f"trend_{name}_hac"]
        assert (h_high - h_low) > (n_high - n_low)


def test_adding_enso_explains_more_variance(results):
    m = results["metrics"]
    assert m["r2_trend_enso"][0] > m["r2_trend_only"][0]


def test_breakpoint_is_inside_its_range_and_warming_accelerates(results):
    year, low, high = results["metrics"]["break_year"]
    assert low <= year <= high
    assert results["metrics"]["slope_after_break"][0] > results["metrics"]["slope_before_break"][0]


def test_adjusted_series_is_observed_minus_enso(results):
    months, worst = results["adjusted"]
    assert months > 600
    assert float(worst) <= 0.0015                              # rounding to 3 decimals only
