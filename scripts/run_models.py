"""Statistical models for the climate-drivers analysis. Results are written to the database.

Usage:
    python scripts/run_models.py

Models (details and caveats: docs/METHODS.md)
  1. Trend + ENSO, monthly, 1970 onwards:
         anomaly = a + b * time + c * ONI(t - k) + error
     The lag k (0–6 months) is chosen by AIC. Standard errors are computed twice:
     classical OLS and Newey-West (HAC), which allows for autocorrelated errors.
  2. ENSO-adjusted series: observed - c * ONI(t - k).
  3. Linear trend of annual means since 1970: classical vs Newey-West confidence interval.
  4. Breakpoint: continuous two-segment ("hinge") trend on annual means since 1880; every
     candidate year is fitted, the profile is stored, and an approximate 95% range is
     derived from an F test on the residual sum of squares.
Outputs: model_results, model_enso_adjusted, model_breakpoints (one transaction).
"""

from __future__ import annotations

import math
import sys

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

from db import get_connection

MODEL_START = 1970
MAX_LAG = 6
BREAK_CANDIDATES = range(1910, 2011)
CONFIDENCE = 0.95


def newey_west_lags(n: int) -> int:
    """Common rule of thumb for the HAC bandwidth: floor(4 * (n / 100) ** (2/9))."""
    return int(math.floor(4 * (n / 100) ** (2 / 9)))


def load(cur) -> tuple[pd.DataFrame, pd.Series]:
    cur.execute("""SELECT obs_date, anomaly::float FROM v_monthly
                   WHERE region = 'GLB' AND anomaly IS NOT NULL ORDER BY obs_date""")
    temp = pd.DataFrame(cur.fetchall(), columns=["obs_date", "anomaly"])
    temp["obs_date"] = pd.to_datetime(temp.obs_date)
    cur.execute("SELECT obs_date, oni::float FROM v_enso ORDER BY obs_date")
    oni = pd.DataFrame(cur.fetchall(), columns=["obs_date", "oni"])
    oni = oni.set_index(pd.to_datetime(oni.obs_date)).oni
    return temp, oni


def with_lag(temp: pd.DataFrame, oni: pd.Series, lag: int) -> pd.DataFrame:
    frame = temp.copy()
    frame["oni_lag"] = oni.reindex(frame.obs_date - pd.DateOffset(months=lag)).values
    frame["years"] = frame.obs_date.dt.year + (frame.obs_date.dt.month - 1) / 12
    return frame[frame.obs_date.dt.year >= MODEL_START].dropna()


def fit_enso_model(temp: pd.DataFrame, oni: pd.Series):
    # Compare lags on the SAME months (those where every lag is available), then refit.
    common = with_lag(temp, oni, MAX_LAG).obs_date
    aic = {}
    for lag in range(MAX_LAG + 1):
        frame = with_lag(temp, oni, lag)
        frame = frame[frame.obs_date.isin(common)]
        aic[lag] = sm.OLS(frame.anomaly, sm.add_constant(frame[["years", "oni_lag"]])).fit().aic
    lag = min(aic, key=aic.get)

    frame = with_lag(temp, oni, lag)
    X = sm.add_constant(frame[["years", "oni_lag"]])
    naive = sm.OLS(frame.anomaly, X).fit()
    maxlags = newey_west_lags(len(frame))
    hac = sm.OLS(frame.anomaly, X).fit(cov_type="HAC", cov_kwds={"maxlags": maxlags})
    trend_only = sm.OLS(frame.anomaly, sm.add_constant(frame[["years"]])).fit()
    return lag, aic, frame, naive, hac, trend_only, maxlags


def annual_means(temp: pd.DataFrame) -> pd.DataFrame:
    year = temp.obs_date.dt.year
    annual = temp.groupby(year).anomaly.agg(["mean", "count"])
    annual = annual[annual["count"] == 12]["mean"].rename("anomaly").reset_index()
    return annual.rename(columns={"obs_date": "year"})


def hinge_profile(annual: pd.DataFrame) -> tuple[pd.DataFrame, int, tuple[int, int]]:
    """Fit anomaly = a + b*year + c*max(0, year - k) for every k; keep the SSE profile."""
    years, y = annual.year.values.astype(float), annual.anomaly.values
    rows = []
    for k in BREAK_CANDIDATES:
        X = np.column_stack([np.ones_like(years), years, np.maximum(0, years - k)])
        coef, *_ = np.linalg.lstsq(X, y, rcond=None)
        sse = float(np.sum((y - X @ coef) ** 2))
        rows.append((k, sse, coef[1] * 10, (coef[1] + coef[2]) * 10))
    profile = pd.DataFrame(rows, columns=["break_year", "sse", "slope_before", "slope_after"])
    best = profile.loc[profile.sse.idxmin()]
    # Approximate 95% range: breakpoints whose SSE is not significantly worse (F test, 1 df).
    n, params = len(y), 4
    threshold = best.sse * (1 + stats.f.ppf(CONFIDENCE, 1, n - params) / (n - params))
    plausible = profile[profile.sse <= threshold].break_year
    return profile, int(best.break_year), (int(plausible.min()), int(plausible.max()))


def main() -> int:
    with get_connection() as conn, conn.cursor() as cur:
        temp, oni = load(cur)
        lag, aic, frame, naive, hac, trend_only, maxlags = fit_enso_model(temp, oni)

        # ENSO-adjusted series
        enso_part = hac.params["oni_lag"] * frame.oni_lag
        adjusted = pd.DataFrame({
            "obs_date": frame.obs_date.dt.date,
            "observed": frame.anomaly.round(3),
            "enso_component": enso_part.round(3),
            "adjusted": (frame.anomaly - enso_part).round(3),
        })

        # Annual trend since 1970: classical vs Newey-West interval
        annual = annual_means(temp)
        recent = annual[annual.year >= MODEL_START]
        Xa = sm.add_constant(recent[["year"]].astype(float))
        annual_naive = sm.OLS(recent.anomaly, Xa).fit()
        annual_maxlags = newey_west_lags(len(recent))
        annual_hac = sm.OLS(recent.anomaly, Xa).fit(cov_type="HAC", cov_kwds={"maxlags": annual_maxlags})

        profile, break_year, (break_low, break_high) = hinge_profile(annual)
        best = profile.set_index("break_year").loc[break_year]

        residual_ac1 = float(pd.Series(naive.resid.values).autocorr(1))
        ci_n, ci_h = naive.conf_int(1 - CONFIDENCE), hac.conf_int(1 - CONFIDENCE)
        ca_n, ca_h = annual_naive.conf_int(1 - CONFIDENCE), annual_hac.conf_int(1 - CONFIDENCE)
        period = f"{frame.obs_date.min():%Y-%m}–{frame.obs_date.max():%Y-%m}"
        results = [
            ("enso_lag_months", lag, None, None, "months",
             f"lag of ONI with the lowest AIC among 0–{MAX_LAG} months, monthly OLS {period}"),
            ("enso_coefficient", hac.params["oni_lag"], ci_h.loc["oni_lag", 0], ci_h.loc["oni_lag", 1],
             "°C per ONI unit", f"monthly OLS trend + ENSO {period}, Newey-West CI (maxlags={maxlags})"),
            ("trend_monthly_naive", naive.params["years"] * 10, ci_n.loc["years", 0] * 10, ci_n.loc["years", 1] * 10,
             "°C per decade", f"monthly OLS trend + ENSO {period}, classical CI"),
            ("trend_monthly_hac", hac.params["years"] * 10, ci_h.loc["years", 0] * 10, ci_h.loc["years", 1] * 10,
             "°C per decade", f"monthly OLS trend + ENSO {period}, Newey-West CI (maxlags={maxlags})"),
            ("r2_trend_only", trend_only.rsquared, None, None, "share of variance",
             f"monthly OLS trend only {period}"),
            ("r2_trend_enso", naive.rsquared, None, None, "share of variance",
             f"monthly OLS trend + ENSO {period}"),
            ("residual_autocorrelation_lag1", residual_ac1, None, None, "correlation",
             "lag-1 autocorrelation of monthly residuals (why Newey-West is needed)"),
            ("trend_annual_naive", annual_naive.params["year"] * 10, ca_n.loc["year", 0] * 10, ca_n.loc["year", 1] * 10,
             "°C per decade", f"annual means {MODEL_START}–{recent.year.max()}, classical CI"),
            ("trend_annual_hac", annual_hac.params["year"] * 10, ca_h.loc["year", 0] * 10, ca_h.loc["year", 1] * 10,
             "°C per decade", f"annual means {MODEL_START}–{recent.year.max()}, Newey-West CI (maxlags={annual_maxlags})"),
            ("break_year", break_year, break_low, break_high, "year",
             f"two-segment hinge fit on annual means {annual.year.min()}–{annual.year.max()}, "
             f"approx. 95% range from an F test on the SSE profile"),
            ("slope_before_break", best.slope_before, None, None, "°C per decade", "hinge fit, before the breakpoint"),
            ("slope_after_break", best.slope_after, None, None, "°C per decade", "hinge fit, after the breakpoint"),
        ]
        yearly = adjusted.assign(year=pd.to_datetime(adjusted.obs_date).dt.year).groupby("year")
        for year in (2023, 2024, 2025):
            if year in yearly.groups and len(yearly.get_group(year)) == 12:
                group = yearly.get_group(year)
                results.append((f"enso_part_{year}", float(group.enso_component.mean()), None, None, "°C",
                                f"mean ENSO component of {year} (observed {group.observed.mean():.2f})"))

        cur.execute("TRUNCATE model_results, model_enso_adjusted, model_breakpoints")
        cur.executemany(
            "INSERT INTO model_results (metric, value, ci_low, ci_high, unit, method) VALUES (%s, %s, %s, %s, %s, %s)",
            [(m, float(v), None if lo is None else float(lo), None if hi is None else float(hi), u, how)
             for m, v, lo, hi, u, how in results],
        )
        with cur.copy("COPY model_enso_adjusted (obs_date, observed, enso_component, adjusted) FROM STDIN") as copy:
            for row in adjusted.itertuples(index=False):
                copy.write_row(row)
        with cur.copy("COPY model_breakpoints (break_year, sse, slope_before, slope_after) FROM STDIN") as copy:
            for row in profile.itertuples(index=False):
                copy.write_row((int(row.break_year), row.sse, row.slope_before, row.slope_after))

    print(f"OK     ENSO lag chosen by AIC: {lag} months  (AIC: " +
          ", ".join(f"{k}:{v:.0f}" for k, v in aic.items()) + ")")
    print(f"OK     ENSO coefficient: {hac.params['oni_lag']:+.3f} °C per ONI unit "
          f"[{ci_h.loc['oni_lag', 0]:+.3f}, {ci_h.loc['oni_lag', 1]:+.3f}] (Newey-West)")
    print(f"OK     trend {period}: {hac.params['years'] * 10:+.3f} °C/decade | classical CI ±"
          f"{(ci_n.loc['years', 1] - ci_n.loc['years', 0]) * 5:.3f} | Newey-West CI ±"
          f"{(ci_h.loc['years', 1] - ci_h.loc['years', 0]) * 5:.3f}")
    print(f"OK     R²: trend only {trend_only.rsquared:.3f} -> trend + ENSO {naive.rsquared:.3f}; "
          f"residual lag-1 autocorrelation {residual_ac1:.2f}")
    print(f"OK     annual trend since {MODEL_START}: {annual_hac.params['year'] * 10:+.3f} °C/decade | "
          f"classical ±{(ca_n.loc['year', 1] - ca_n.loc['year', 0]) * 5:.3f} | "
          f"Newey-West ±{(ca_h.loc['year', 1] - ca_h.loc['year', 0]) * 5:.3f}")
    print(f"OK     breakpoint: {break_year} (approx. 95% range {break_low}–{break_high}); "
          f"{best.slope_before:+.3f} -> {best.slope_after:+.3f} °C/decade")
    for m, v, *_ in results:
        if m.startswith("enso_part_"):
            print(f"OK     {m}: {v:+.3f} °C")
    print(f"OK     model_enso_adjusted: {len(adjusted)} months, model_breakpoints: {len(profile)} candidates")
    return 0


if __name__ == "__main__":
    sys.exit(main())
