# Methods: climate drivers, ENSO and trend analysis

This document describes the statistical part of the project — `sql/drivers_queries.sql`,
`scripts/run_models.py` and the **Climate Drivers** page — and states what the results can and
cannot show. All numbers below come from `model_results` for the NASA snapshot of 10 Nov 2026,
the NOAA ONI file of 3 Nov 2026 and the NOAA Mauna Loa file of 19 Nov 2026.

## 1. Research question

How much of the year-to-year variation in global surface temperature is associated with the
El Niño–Southern Oscillation (ENSO), how fast is the underlying trend once that variation is
accounted for, and when did the warming accelerate?

## 2. Data

| Series | Source | Period | Notes |
|---|---|---|---|
| Global monthly temperature anomaly | NASA GISS GISTEMP v4 | 1880–2026 | °C relative to 1951–1980 |
| Oceanic Niño Index (ONI) | NOAA Climate Prediction Center | 1950–2026 | 3-month running mean of the Niño 3.4 sea-surface temperature anomaly (ERSSTv5) |
| Atmospheric CO₂ | NOAA Global Monitoring Laboratory, Mauna Loa | 1958–2026 | monthly mean and seasonally adjusted, ppm |

**Alignment.** NOAA labels each ONI value by its 3-month season (DJF, JFM, …). Each value is
stored on the **centre month** of its window (DJF → January, NDJ → December) so that it can be
joined month by month with temperature. **Missing values.** NOAA's sentinels for "not
available" (`-1`, `-9.99`) are stored as `NULL`; validation rejects any gap or duplicate month
and checks that annual CO₂ increases every year since 1959.

ENSO phases follow NOAA's threshold applied to single values: El Niño if ONI ≥ +0.5,
La Niña if ONI ≤ −0.5, otherwise neutral. (NOAA's official episode definition additionally
requires five consecutive overlapping seasons; the single-value rule is a simplification.)

## 3. Exploratory analysis in SQL (`sql/drivers_queries.sql`)

**Detrending (D2, D3).** Comparing El Niño and La Niña years directly would confound ENSO with
the long-term warming, because recent years are both warmer and more often observed. A linear
trend is fitted inside SQL with `regr_slope` / `regr_intercept` and subtracted; the remaining
departures are compared.

- **D2 — phase comparison.** Each year since 1951 is classified by its winter (DJF) ONI, since
  ENSO peaks in northern winter. Mean departure from the trend: El Niño **+0.052 °C**
  (25 years), neutral +0.025 °C (24), La Niña **−0.073 °C** (26).
- **D3 — lagged correlation.** The detrended monthly anomaly is correlated with the ONI of
  *k* months earlier, *k* = 0 … 12 (`generate_series` + a join shifted by
  `make_interval(months => k)`). The correlation peaks at *k* = 1–3 months (maximum r = 0.42 at
  2 months) and decays afterwards.
- **D7 — CO₂.** The annual global anomaly regressed on annual mean CO₂ (1959–2025) gives
  1.08 °C per 100 ppm with R² = 0.94. This is reported as an **association between two rising
  series**, not as a sensitivity estimate (see §7).

## 4. Regression model (`scripts/run_models.py`)

Monthly global anomaly *y* from January 1970 to the latest month (*n* = 682):

    y_t = β₀ + β₁ · time_t + β₂ · ONI_{t−k} + ε_t

- **Period.** 1970 onwards, where the trend is close to linear (§6). Fitting from 1950 with a
  single straight line would leave the slow-then-fast curvature in the residuals, where part of
  it could be absorbed by the ENSO term.
- **Lag selection.** *k* is chosen by the Akaike Information Criterion among 0–6 months, with
  all candidate models fitted on the same months. AIC selects **k = 3** (AIC −813; *k* = 2:
  −810). The SQL correlation (D3, 1950 onwards) peaks at 2 months; a test checks that both
  methods agree within one month.
- **Estimation.** Ordinary least squares (statsmodels).

| Estimate | Value | 95% interval (Newey-West) |
|---|---|---|
| ENSO coefficient β₂ | **+0.091 °C per ONI unit** | [+0.071, +0.110] |
| Trend β₁ | **+0.202 °C per decade** | [+0.189, +0.214] |
| R², trend only → trend + ENSO | 0.829 → **0.870** | |

A strong El Niño (ONI ≈ +2.5) is therefore associated with a temporary global warming of about
+0.2 °C, three months later.

### 4.1 Autocorrelation and Newey-West standard errors

OLS standard errors assume independent errors. Monthly temperature residuals are strongly
autocorrelated (lag-1 autocorrelation **0.59**): each month resembles the previous one, so the
data contain much less independent information than *n* suggests, and classical intervals are
too narrow. Heteroskedasticity- and autocorrelation-consistent (HAC) standard errors
(Newey & West, 1987) correct this. The bandwidth follows the common rule
`floor(4 · (n/100)^(2/9))`: 6 lags for the monthly model, 3 for annual means.

| Trend since 1970 (°C / decade) | Classical 95% interval | Newey-West 95% interval |
|---|---|---|
| Monthly model with ENSO | ± 0.006 | **± 0.012** |
| Annual means | ± 0.017 | **± 0.022** |

The point estimate does not change; the honest uncertainty is about **twice** the classical one
for monthly data.

### 4.2 ENSO-adjusted series

    adjusted_t = y_t − β̂₂ · ONI_{t−3}

stored in `model_enso_adjusted` (682 months). This is the temperature series with the linear
ENSO signal removed — in the spirit of Foster & Rahmstorf (2011), who also removed volcanic and
solar signals. Annual means of the ENSO component: 2016 **+0.11 °C**, 2023 +0.01 °C,
2024 +0.09 °C, 2025 −0.02 °C. Ranked by the adjusted series (D8), 2016 falls from the 4th to the
9th warmest year, while 2023–2025 remain the three warmest; 2025 becomes the warmest.

The model attributes almost none of 2023's jump to ENSO: El Niño only developed in mid-2023 and
acts with a three-month lag. With this model, the 2023 anomaly is largely **unexplained** by
ENSO; it is not claimed here what explains it.

## 5. Breakpoint analysis

Annual global means, 1880–2025, are fitted with a continuous two-segment ("hinge") trend:

    y = a + b · year + c · max(0, year − K)

for every candidate breakpoint *K* = 1910 … 2010 (least squares). The profile of the residual sum
of squares is stored in `model_breakpoints`. The best fit is **K = 1975**, with a slope of
+0.036 °C per decade before and **+0.205 °C per decade after** — about five times faster.

An approximate 95% range for *K* collects every breakpoint whose residual sum of squares is not
significantly worse than the best one under an *F* test with one degree of freedom:
**1971–1979**. This range ignores autocorrelation (§7) and is likely too narrow.

## 6. Validation and reproducibility

- `tests/test_drivers.py` checks the season-to-month mapping, NULL handling, gap detection, the
  sign and significance of the ENSO effect, that Newey-West intervals are wider than classical
  ones, that adding ENSO increases R², that the breakpoint lies inside its range, and that
  *adjusted = observed − ENSO component*.
- Every input file is recorded with its SHA-256 checksum in `data/raw/drivers/manifest.json`;
  `python scripts/run_models.py` reproduces every number in this document.

## 7. Limitations

1. **Association, not attribution.** None of these regressions establishes cause. The
   CO₂–temperature regression in particular relates two series that both rise over time; the
   evidence that CO₂ warms the climate comes from radiative physics and climate models, not
   from this correlation.
2. **Omitted drivers.** Volcanic aerosols (e.g. Pinatubo, 1991) and solar variability are not
   in the model; their effects remain in the residuals and in the "adjusted" series.
3. **Linearity.** ENSO is assumed to act linearly and with a single lag; real ENSO effects are
   asymmetric and seasonally dependent.
4. **One ENSO index.** ONI summarises ENSO by a single regional sea-surface temperature series.
5. **Breakpoint uncertainty.** The *F*-based range assumes independent errors and a single
   abrupt change in slope; with autocorrelated data the true uncertainty is wider.
6. **Single dataset.** Only GISTEMP is used; other global temperature datasets differ slightly.

## References

- Foster, G. and Rahmstorf, S. (2011). Global temperature evolution 1979–2010.
  *Environmental Research Letters*, 6, 044022.
- Huang, B. et al. (2017). Extended Reconstructed Sea Surface Temperature, version 5 (ERSSTv5):
  upgrades, validations, and intercomparisons. *Journal of Climate*, 30, 8179–8205.
- Lenssen, N. J. L. et al. (2019). Improvements in the GISTEMP uncertainty model.
  *Journal of Geophysical Research: Atmospheres*, 124, 6307–6326.
- Newey, W. K. and West, K. D. (1987). A simple, positive semi-definite, heteroskedasticity and
  autocorrelation consistent covariance matrix. *Econometrica*, 55, 703–708.
- NOAA Climate Prediction Center. Oceanic Niño Index (ONI).
  https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt
- NOAA Global Monitoring Laboratory. Trends in atmospheric carbon dioxide, Mauna Loa.
  https://gml.noaa.gov/ccgg/trends/
- GISTEMP Team (2026). GISS Surface Temperature Analysis (GISTEMP), version 4. NASA Goddard
  Institute for Space Studies. https://data.giss.nasa.gov/gistemp/
