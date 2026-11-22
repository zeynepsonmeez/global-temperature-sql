"""Unit tests for the statistical helpers in scripts/run_models.py (no database needed)."""

import numpy as np
import pandas as pd
import pytest

import run_models as rm


def test_newey_west_bandwidth_rule():
    # floor(4 * (n/100) ** (2/9)): the values used in docs/METHODS.md
    assert rm.newey_west_lags(682) == 6
    assert rm.newey_west_lags(56) == 3
    assert rm.newey_west_lags(100) == 4


def test_hinge_profile_recovers_a_known_breakpoint():
    """Synthetic series: flat until 1975, then +0.2 °C per decade, plus small noise."""
    rng = np.random.default_rng(42)
    years = np.arange(1880, 2026)
    truth = np.where(years < 1975, 0.0, (years - 1975) * 0.02)
    annual = pd.DataFrame({"year": years, "anomaly": truth + rng.normal(0, 0.03, len(years))})

    profile, best, (low, high) = rm.hinge_profile(annual)

    assert abs(best - 1975) <= 2
    assert low <= best <= high and low <= 1975 <= high
    row = profile.set_index("break_year").loc[best]
    assert row.slope_before == pytest.approx(0.0, abs=0.02)      # °C per decade
    assert row.slope_after == pytest.approx(0.2, abs=0.02)


def test_hinge_profile_covers_every_candidate_year():
    annual = pd.DataFrame({"year": np.arange(1880, 2026), "anomaly": np.linspace(-0.3, 1.2, 146)})
    profile, _, _ = rm.hinge_profile(annual)
    assert list(profile.break_year) == list(rm.BREAK_CANDIDATES)


def test_annual_means_keep_complete_years_only():
    dates = pd.date_range("2000-01-01", "2001-06-01", freq="MS")         # 2001 has only 6 months
    temp = pd.DataFrame({"obs_date": dates, "anomaly": np.arange(len(dates), dtype=float)})
    annual = rm.annual_means(temp)
    assert list(annual.year) == [2000]
    assert annual.anomaly.iloc[0] == pytest.approx(np.arange(12).mean())


def test_with_lag_shifts_the_index_by_whole_months():
    dates = pd.date_range("1969-01-01", "1971-12-01", freq="MS")
    temp = pd.DataFrame({"obs_date": dates, "anomaly": 0.0})
    oni = pd.Series(np.arange(len(dates), dtype=float), index=dates)    # value = month number
    frame = rm.with_lag(temp, oni, lag=3)
    first = frame.iloc[0]
    assert first.obs_date == pd.Timestamp("1970-01-01")                  # model starts in 1970
    assert first.oni_lag == oni[pd.Timestamp("1969-10-01")]              # three months earlier
