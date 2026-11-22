# 0007 — Trend + ENSO regression from 1970 with Newey-West errors

**Status:** Accepted

## Context

The Climate Drivers analysis separates the long-term trend from El Niño / La Niña variability
and reports its uncertainty. Monthly temperature residuals are strongly autocorrelated.

## Decision

- Model `anomaly = a + b·time + c·ONI(t−k) + error` on monthly data **from 1970**, where the
  trend is close to linear. Starting in 1950 would leave the trend's curvature in the
  residuals, where part of it could be absorbed by the ENSO term.
- Choose the lag *k* by **AIC** over 0–6 months, all candidates fitted on the same months;
  check it against the SQL lagged-correlation query (they agree within one month).
- Report **Newey-West (HAC)** intervals with the rule-of-thumb bandwidth
  `floor(4 · (n/100)^(2/9))`, next to the classical intervals.
- Store every result in the database (`model_results`, `model_enso_adjusted`,
  `model_breakpoints`) so the app and the SQL library read them, and document them in
  `docs/METHODS.md`.

## Consequences

- The classical interval for the trend is about half as wide as the Newey-West one; the app
  shows both to make the point.
- Results are described as associations; limitations (omitted volcanic and solar drivers,
  linear ENSO effect, an *F*-based breakpoint range that ignores autocorrelation) are listed.

## Alternatives considered

- **Classical OLS errors:** overstate certainty with autocorrelated data.
- **ARIMA errors / GLS:** more efficient, but harder to explain; HAC keeps OLS estimates and
  only corrects the uncertainty.
- **Full attribution model (volcanic, solar):** closer to the literature; left as future work.
