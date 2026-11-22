-- =============================================================================
-- GlobalTemperatureSQL — Climate drivers: ENSO (El Niño / La Niña) and CO2
-- Topics: detrending with regr_slope/regr_intercept, lagged joins with make_interval,
--         generate_series + correlation, LAG growth rates, VALUES lists, ranking
-- Objects: v_monthly, v_enso (ONI, phase), v_co2, model_enso_adjusted, model_breakpoints
-- Statements of association only: see docs/METHODS.md for what these numbers do NOT show.
-- =============================================================================


-- D1. The strongest El Niño and La Niña peaks since 1950
-- An ENSO event is summarised by its most extreme 3-month ONI within the year.
WITH yearly AS (
    SELECT EXTRACT(YEAR FROM obs_date)::int AS year, MAX(oni) AS max_oni, MIN(oni) AS min_oni
    FROM   v_enso
    GROUP  BY EXTRACT(YEAR FROM obs_date)
)
(SELECT 'El Nino' AS event, year, max_oni AS peak_oni FROM yearly ORDER BY max_oni DESC LIMIT 5)
UNION ALL
(SELECT 'La Nina' AS event, year, min_oni AS peak_oni FROM yearly ORDER BY min_oni ASC LIMIT 5);


-- D2. How much warmer are El Niño years, once the long-term trend is removed?
-- Without detrending, El Niño years would look warm simply because recent years are warm.
-- The fitted line (regr_slope / regr_intercept) is subtracted first; what remains is the
-- year-to-year departure. Each year is classified by its winter (DJF) ONI, because ENSO
-- peaks in northern winter and global temperature follows a few months later.
WITH annual AS (
    SELECT year, AVG(anomaly) AS anomaly
    FROM   v_monthly
    WHERE  region = 'GLB' AND year >= 1951
    GROUP  BY year
    HAVING COUNT(anomaly) = 12
),
fit AS (
    SELECT regr_slope(anomaly, year) AS slope, regr_intercept(anomaly, year) AS intercept
    FROM   annual
),
winter AS (
    SELECT EXTRACT(YEAR FROM obs_date)::int AS year, phase
    FROM   v_enso
    WHERE  season = 'DJF'
)
SELECT w.phase,
       COUNT(*)                                                            AS years,
       ROUND(AVG(a.anomaly - (f.slope * a.year + f.intercept))::numeric, 3) AS mean_departure_from_trend,
       ROUND(MIN(a.anomaly - (f.slope * a.year + f.intercept))::numeric, 3) AS lowest,
       ROUND(MAX(a.anomaly - (f.slope * a.year + f.intercept))::numeric, 3) AS highest
FROM   annual a
JOIN   winter w USING (year)
CROSS  JOIN fit f
GROUP  BY w.phase
ORDER  BY mean_departure_from_trend DESC;


-- D3. How many months later does ENSO show up in global temperature? (lagged correlation)
-- Temperature is detrended, then correlated with the ONI of k months EARLIER, for k = 0..12.
-- generate_series produces the lags; make_interval shifts the join by k months.
-- The lag with the highest correlation is used by the regression model (scripts/run_models.py).
WITH temp AS (
    SELECT obs_date, anomaly, (year * 12 + month)::float AS t
    FROM   v_monthly
    WHERE  region = 'GLB' AND year >= 1950 AND anomaly IS NOT NULL
),
fit AS (
    SELECT regr_slope(anomaly, t) AS slope, regr_intercept(anomaly, t) AS intercept FROM temp
),
detrended AS (
    SELECT temp.obs_date, temp.anomaly - (fit.slope * temp.t + fit.intercept) AS departure
    FROM   temp CROSS JOIN fit
)
SELECT k                                           AS lag_months,
       ROUND(corr(e.oni, d.departure)::numeric, 3) AS correlation,
       COUNT(*)                                    AS months
FROM   generate_series(0, 12) AS k
JOIN   detrended d ON TRUE
JOIN   v_enso    e ON e.obs_date = d.obs_date - make_interval(months => k)
GROUP  BY k
ORDER  BY k;


-- D4. Warm years despite La Niña: rank of each La Niña year among all years
-- A La Niña cools the globe temporarily — yet recent La Niña years still rank near the top.
WITH annual AS (
    SELECT year, AVG(anomaly) AS anomaly,
           RANK() OVER (ORDER BY AVG(anomaly) DESC) AS warmest_rank
    FROM   v_monthly
    WHERE  region = 'GLB'
    GROUP  BY year
    HAVING COUNT(anomaly) = 12
)
SELECT a.year, ROUND(a.anomaly, 2) AS anomaly, a.warmest_rank, e.oni AS winter_oni
FROM   annual a
JOIN   v_enso e ON e.obs_date = make_date(a.year, 1, 1)
WHERE  e.phase = 'La Nina'
ORDER  BY a.warmest_rank
LIMIT  8;


-- D5. CO2 growth rate per decade (ppm per year)
-- LAG gives last year's mean; the yearly difference is the growth, averaged per decade.
WITH annual AS (
    SELECT EXTRACT(YEAR FROM obs_date)::int AS year, AVG(co2_ppm) AS co2
    FROM   v_co2
    GROUP  BY EXTRACT(YEAR FROM obs_date)
    HAVING COUNT(*) = 12
),
growth AS (
    SELECT year, co2, co2 - LAG(co2) OVER (ORDER BY year) AS ppm_per_year
    FROM   annual
)
SELECT (year / 10) * 10                    AS decade,
       ROUND(MIN(co2), 1)                  AS co2_start,
       ROUND(MAX(co2), 1)                  AS co2_end,
       ROUND(AVG(ppm_per_year), 2)         AS mean_growth_ppm_per_year
FROM   growth
WHERE  ppm_per_year IS NOT NULL
GROUP  BY decade
ORDER  BY decade;


-- D6. When did CO2 first pass 350, 400 and 420 ppm? (a VALUES list joined LATERALly)
SELECT t.threshold_ppm,
       f.first_month,
       EXTRACT(YEAR FROM f.first_month)
     - LAG(EXTRACT(YEAR FROM f.first_month)) OVER (ORDER BY t.threshold_ppm) AS years_after_previous
FROM  (VALUES (350), (400), (420)) AS t(threshold_ppm)
CROSS JOIN LATERAL (
        SELECT MIN(c.obs_date) AS first_month
        FROM   v_co2 c
        WHERE  c.co2_deseason >= t.threshold_ppm
      ) f
ORDER BY t.threshold_ppm;


-- D7. Temperature and CO2 rise together: degrees per 100 ppm, 1959 onwards
-- A statistical association between two rising series — NOT a measurement of cause.
-- Physics, not this regression, is the evidence that CO2 warms the planet.
WITH annual AS (
    SELECT m.year, AVG(m.anomaly) AS anomaly, AVG(c.co2_ppm) AS co2
    FROM   v_monthly m
    JOIN   v_co2     c ON c.obs_date = m.obs_date
    WHERE  m.region = 'GLB'
    GROUP  BY m.year
    HAVING COUNT(*) = 12
)
SELECT MIN(year)                                             AS from_year,
       MAX(year)                                             AS to_year,
       ROUND((regr_slope(anomaly, co2) * 100)::numeric, 3)   AS degrees_per_100_ppm,
       ROUND(regr_r2(anomaly, co2)::numeric, 3)              AS r_squared
FROM   annual;


-- D8. Do the record years stay records once ENSO is removed? (model output)
-- model_enso_adjusted is written by scripts/run_models.py: adjusted = observed - ENSO part.
WITH annual AS (
    SELECT EXTRACT(YEAR FROM obs_date)::int AS year,
           AVG(observed)       AS observed,
           AVG(enso_component) AS enso_part,
           AVG(adjusted)       AS adjusted
    FROM   model_enso_adjusted
    GROUP  BY EXTRACT(YEAR FROM obs_date)
    HAVING COUNT(*) = 12
)
SELECT year,
       ROUND(observed, 2)                              AS observed,
       ROUND(enso_part, 2)                             AS enso_part,
       ROUND(adjusted, 2)                              AS enso_adjusted,
       RANK() OVER (ORDER BY observed DESC)            AS rank_observed,
       RANK() OVER (ORDER BY adjusted DESC)            AS rank_adjusted
FROM   annual
ORDER  BY rank_observed
LIMIT  10;


-- D9. When did warming speed up? The best breakpoints of a two-segment trend (model output)
-- model_breakpoints holds the fit for every candidate year; lowest error = best fit.
SELECT break_year,
       ROUND(sse::numeric, 3)          AS residual_sum_of_squares,
       ROUND(slope_before::numeric, 3) AS deg_per_decade_before,
       ROUND(slope_after::numeric, 3)  AS deg_per_decade_after
FROM   model_breakpoints
ORDER  BY sse
LIMIT  5;


-- D10. The longest runs of El Niño and La Niña months (gaps and islands on a category)
-- Same trick as A10: inside one unbroken run, the two row numbers differ by a constant.
WITH runs AS (
    SELECT obs_date,
           phase,
           ROW_NUMBER() OVER (ORDER BY obs_date)
         - ROW_NUMBER() OVER (PARTITION BY phase ORDER BY obs_date) AS run_id
    FROM   v_enso
)
SELECT phase,
       MIN(obs_date) AS run_start,
       MAX(obs_date) AS run_end,
       COUNT(*)      AS months
FROM   runs
WHERE  phase <> 'Neutral'
GROUP  BY phase, run_id
ORDER  BY months DESC, run_start ASC
LIMIT  6;


-- D11. The yearly "breathing" of the planet: CO2's seasonal cycle by calendar month
-- Monthly minus seasonally adjusted CO2 isolates the cycle: northern forests take up CO2
-- in summer and release it in winter.
SELECT EXTRACT(MONTH FROM obs_date)::int    AS month,
       ROUND(AVG(co2_ppm - co2_deseason), 2) AS seasonal_ppm
FROM   v_co2
WHERE  obs_date >= DATE '2000-01-01'
GROUP  BY EXTRACT(MONTH FROM obs_date)
ORDER  BY month;


-- D12. Strong El Niño peaks and the global temperature of the FOLLOWING year (LEAD)
-- Global temperature tends to peak in the year after a strong El Niño winter.
WITH annual AS (
    SELECT year, AVG(anomaly) AS anomaly
    FROM   v_monthly
    WHERE  region = 'GLB'
    GROUP  BY year
    HAVING COUNT(anomaly) = 12
),
peaks AS (
    SELECT EXTRACT(YEAR FROM obs_date)::int AS year, MAX(oni) AS peak_oni
    FROM   v_enso
    GROUP  BY EXTRACT(YEAR FROM obs_date)
)
SELECT p.year,
       p.peak_oni,
       ROUND(a.anomaly, 2)                                   AS anomaly_same_year,
       ROUND(LEAD(a.anomaly) OVER (ORDER BY a.year), 2)      AS anomaly_next_year
FROM   peaks p
JOIN   annual a USING (year)
ORDER  BY p.peak_oni DESC
LIMIT  6;
