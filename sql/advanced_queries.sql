-- =============================================================================
-- GlobalTemperatureSQL — Advanced queries
-- Topics: window functions (RANK, DENSE_RANK, ROW_NUMBER, LAG, moving windows,
--         running MAX), linear regression aggregates (regr_slope, regr_r2)
-- Run:    docker compose exec -T db psql -U gts_admin -d global_temperature < sql/advanced_queries.sql
-- =============================================================================
-- Window functions compute a value for each row from a "window" of related rows,
-- WITHOUT collapsing the rows the way GROUP BY does.


-- A1. Ranking the hottest years: RANK vs DENSE_RANK vs ROW_NUMBER
-- On ties: RANK gives both rows the same rank and SKIPS the next number (1,2,3,4,4,6);
-- DENSE_RANK does not skip (1,2,3,4,4,5); ROW_NUMBER never ties (1,2,3,4,5,6).
WITH annual AS (
    SELECT year, ROUND(AVG(anomaly), 2) AS anomaly
    FROM   v_monthly
    WHERE  region = 'GLB'
    GROUP  BY year
    HAVING COUNT(anomaly) = 12
)
SELECT year,
       anomaly,
       RANK()       OVER (ORDER BY anomaly DESC) AS rank,
       DENSE_RANK() OVER (ORDER BY anomaly DESC) AS dense_rank,
       ROW_NUMBER() OVER (ORDER BY anomaly DESC, year) AS row_number
FROM   annual
ORDER  BY anomaly DESC, year
LIMIT  8;


-- A2. Largest year-over-year jumps (LAG)
-- LAG(x) returns x from the previous row in the window's order — here, last year.
WITH annual AS (
    SELECT year, AVG(anomaly) AS anomaly
    FROM   v_monthly
    WHERE  region = 'GLB'
    GROUP  BY year
    HAVING COUNT(anomaly) = 12
)
SELECT year,
       ROUND(anomaly, 2)                                         AS anomaly,
       ROUND(LAG(anomaly) OVER (ORDER BY year), 2)               AS previous_year,
       ROUND(anomaly - LAG(anomaly) OVER (ORDER BY year), 2)     AS change
FROM   annual
ORDER  BY change DESC NULLS LAST
LIMIT  5;


-- A3. 5-year centred moving average (rolling window)
-- ROWS BETWEEN 2 PRECEDING AND 2 FOLLOWING = this year, 2 before, 2 after.
-- At the edges the window is incomplete; CASE returns NULL there instead of
-- a misleading average of fewer than 5 years.
WITH annual AS (
    SELECT year, AVG(anomaly) AS anomaly
    FROM   v_monthly
    WHERE  region = 'GLB'
    GROUP  BY year
    HAVING COUNT(anomaly) = 12
)
SELECT year,
       ROUND(anomaly, 2) AS anomaly,
       CASE WHEN COUNT(*) OVER w = 5 THEN ROUND(AVG(anomaly) OVER w, 2) END AS moving_avg_5y
FROM   annual
WINDOW w AS (ORDER BY year ROWS BETWEEN 2 PRECEDING AND 2 FOLLOWING)
ORDER  BY year DESC
LIMIT  10;


-- A4. Record-breaking years: warmer than every year before them (running MAX)
-- The window ends at "1 PRECEDING", so the current year is compared only with the past.
WITH annual AS (
    SELECT year, AVG(anomaly) AS anomaly
    FROM   v_monthly
    WHERE  region = 'GLB'
    GROUP  BY year
    HAVING COUNT(anomaly) = 12
),
with_previous_max AS (
    SELECT year,
           anomaly,
           MAX(anomaly) OVER (ORDER BY year
                              ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING) AS previous_record
    FROM   annual
)
SELECT year,
       ROUND(anomaly, 2)                    AS anomaly,
       ROUND(previous_record, 2)            AS previous_record,
       ROUND(anomaly - previous_record, 2)  AS margin
FROM   with_previous_max
WHERE  anomaly > previous_record
  AND  year >= 1980
ORDER  BY year;


-- A5. Hottest month of each recent year (ROW_NUMBER with PARTITION BY)
-- PARTITION BY restarts the numbering for every year; row 1 is that year's top month.
WITH ranked AS (
    SELECT year,
           month,
           anomaly,
           ROW_NUMBER() OVER (PARTITION BY year ORDER BY anomaly DESC NULLS LAST) AS rn
    FROM   v_monthly
    WHERE  region = 'GLB'
      AND  year >= 2015
)
SELECT year, month AS hottest_month, anomaly
FROM   ranked
WHERE  rn = 1
ORDER  BY year;


-- A6. Warming rate in °C per decade (linear regression)
-- regr_slope(y, x) is the least-squares slope of y against x: °C per year, × 10 per decade.
-- regr_r2 (0–1) says how well a straight line fits the period.
WITH annual AS (
    SELECT region, year, AVG(anomaly) AS anomaly
    FROM   v_monthly
    GROUP  BY region, year
    HAVING COUNT(anomaly) = 12
)
SELECT region,
       ROUND((regr_slope(anomaly, year) FILTER (WHERE year >= 1880) * 10)::numeric, 3) AS rate_since_1880,
       ROUND((regr_slope(anomaly, year) FILTER (WHERE year >= 1970) * 10)::numeric, 3) AS rate_since_1970,
       ROUND((regr_r2(anomaly, year)    FILTER (WHERE year >= 1970))::numeric, 2)      AS r2_since_1970
FROM   annual
GROUP  BY region
ORDER  BY region;


-- A7. Arctic amplification: warming rate of each latitude band since 1970
-- Compared with the global rate, so "x_global" > 1 means the band warms faster.
WITH band_rates AS (
    SELECT a.region,
           r.lat_max,
           regr_slope(a.anomaly, a.year) * 10 AS rate
    FROM   v_annual a
    JOIN   regions  r ON r.code = a.region
    WHERE  r.kind = 'zonal'
      AND  a.year >= 1970
    GROUP  BY a.region, r.lat_max
),
global_rate AS (
    SELECT regr_slope(anomaly, year) * 10 AS rate
    FROM  (SELECT year, AVG(anomaly) AS anomaly
           FROM   v_monthly
           WHERE  region = 'GLB' AND year >= 1970
           GROUP  BY year
           HAVING COUNT(anomaly) = 12) g
)
SELECT b.region,
       ROUND(b.rate::numeric, 3)           AS rate_per_decade,
       ROUND((b.rate / g.rate)::numeric, 1) AS x_global
FROM   band_rates b
CROSS  JOIN global_rate g
ORDER  BY b.lat_max DESC;
