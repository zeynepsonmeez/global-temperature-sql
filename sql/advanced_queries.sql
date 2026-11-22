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
       ROW_NUMBER() OVER (ORDER BY anomaly DESC, year ASC) AS row_number
FROM   annual
ORDER  BY anomaly DESC, year ASC
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


-- A8. Quartiles of years (NTILE)
-- NTILE(4) splits the ordered years into 4 equal-sized groups: 1 = coolest quarter.
WITH annual AS (
    SELECT year, AVG(anomaly) AS anomaly
    FROM   v_monthly
    WHERE  region = 'GLB'
    GROUP  BY year
    HAVING COUNT(anomaly) = 12
),
quartiles AS (
    SELECT year, anomaly, NTILE(4) OVER (ORDER BY anomaly) AS quartile
    FROM   annual
)
SELECT quartile,
       COUNT(*)               AS years,
       ROUND(MIN(anomaly), 2) AS from_anomaly,
       ROUND(MAX(anomaly), 2) AS to_anomaly,
       MIN(year)              AS earliest_year,
       MAX(year)              AS latest_year
FROM   quartiles
GROUP  BY quartile
ORDER  BY quartile;


-- A9. How unusual were the last 12 months? (RANK and PERCENT_RANK per calendar month)
-- PARTITION BY month compares each month only with the same month in other years
-- ("the warmest October ever"). PERCENT_RANK: 0 = lowest, 1 = highest on record.
WITH ranked AS (
    SELECT obs_date,
           anomaly,
           RANK()         OVER (PARTITION BY month ORDER BY anomaly DESC NULLS LAST) AS rank_for_month,
           PERCENT_RANK() OVER (PARTITION BY month ORDER BY anomaly)                 AS percentile
    FROM   v_monthly
    WHERE  region = 'GLB'
)
SELECT to_char(obs_date, 'Mon YYYY')  AS month,
       anomaly,
       rank_for_month,
       ROUND(percentile::numeric, 3)  AS percentile
FROM   ranked
WHERE  obs_date > (SELECT MAX(latest.obs_date) FROM v_monthly latest) - INTERVAL '12 months'
ORDER  BY obs_date;


-- A10. Longest streaks of consecutive months at or above +1.0 °C ("gaps and islands")
-- Trick: row number over ALL months minus row number within the "hot" months is
-- constant inside an unbroken run, so it works as a group id for each streak.
WITH flagged AS (
    SELECT obs_date, (anomaly >= 1.0) AS hot
    FROM   v_monthly
    WHERE  region = 'GLB'
),
grouped AS (
    SELECT obs_date,
           hot,
           ROW_NUMBER() OVER (ORDER BY obs_date)
         - ROW_NUMBER() OVER (PARTITION BY hot ORDER BY obs_date) AS streak_id
    FROM   flagged
)
SELECT to_char(MIN(obs_date), 'Mon YYYY') AS streak_start,
       to_char(MAX(obs_date), 'Mon YYYY') AS streak_end,
       COUNT(*)                           AS months
FROM   grouped
WHERE  hot
GROUP  BY streak_id
ORDER  BY months DESC, MIN(obs_date)
LIMIT  5;


-- A11. How long did each record stand? (LEAD over the record years)
-- LEAD looks at the NEXT row: the year the record was beaten. NULL = still standing.
WITH annual AS (
    SELECT year, AVG(anomaly) AS anomaly
    FROM   v_monthly
    WHERE  region = 'GLB'
    GROUP  BY year
    HAVING COUNT(anomaly) = 12
),
records AS (
    SELECT year, anomaly
    FROM  (SELECT year, anomaly,
                  MAX(anomaly) OVER (ORDER BY year
                                     ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING) AS previous_record
           FROM   annual) t
    WHERE  previous_record IS NULL OR anomaly > previous_record
)
SELECT year                                   AS record_year,
       ROUND(anomaly, 2)                      AS anomaly,
       LEAD(year) OVER (ORDER BY year)        AS beaten_in,
       LEAD(year) OVER (ORDER BY year) - year AS years_standing
FROM   records
ORDER  BY years_standing DESC NULLS FIRST
LIMIT  6;


-- A12. First year the annual mean reached each threshold (generate_series + LATERAL)
-- generate_series builds the threshold list; LATERAL lets the subquery use t.threshold,
-- i.e. it runs once per threshold — like a loop, but declarative.
WITH annual AS (
    SELECT year, AVG(anomaly) AS anomaly
    FROM   v_monthly
    WHERE  region = 'GLB'
    GROUP  BY year
    HAVING COUNT(anomaly) = 12
)
SELECT t.threshold,
       f.first_year,
       f.first_year - LAG(f.first_year) OVER (ORDER BY t.threshold) AS years_after_previous
FROM   generate_series(0.2, 1.2, 0.2) AS t(threshold)
CROSS  JOIN LATERAL (
        SELECT MIN(a.year) AS first_year
        FROM   annual a
        WHERE  a.anomaly >= t.threshold
       ) f
ORDER  BY t.threshold;


-- A13. Subtotals with ROLLUP: NH and SH by period, per hemisphere and overall
-- ROLLUP (region, period) adds rows for (region, all periods) and (all, all).
-- GROUPING(col) = 1 marks the rows where that column was rolled up.
SELECT CASE WHEN GROUPING(region) = 1 THEN '(both)' ELSE region END      AS region,
       CASE WHEN GROUPING(period) = 1 THEN '(all years)' ELSE period END AS period,
       ROUND(AVG(anomaly), 2)                                            AS mean_anomaly
FROM  (SELECT region,
              anomaly,
              CASE WHEN year < 1950 THEN '1880-1949'
                   WHEN year < 2000 THEN '1950-1999'
                   ELSE                  '2000-' END AS period
       FROM   v_monthly
       WHERE  region IN ('NH', 'SH')) t
GROUP  BY ROLLUP (region, period)
ORDER  BY GROUPING(region), region, GROUPING(period), period;


-- A14. Do the hemispheres move together? (corr = Pearson correlation)
-- Over the full record both share the warming trend, so the correlation is high.
-- Year-to-year CHANGES remove the trend and show how much the short-term
-- ups and downs (e.g. El Nino) are shared.
WITH annual AS (
    SELECT year,
           AVG(anomaly) FILTER (WHERE region = 'NH') AS nh,
           AVG(anomaly) FILTER (WHERE region = 'SH') AS sh
    FROM   v_monthly
    WHERE  region IN ('NH', 'SH')
    GROUP  BY year
    HAVING COUNT(anomaly) = 24
),
changes AS (
    SELECT nh - LAG(nh) OVER (ORDER BY year) AS d_nh,
           sh - LAG(sh) OVER (ORDER BY year) AS d_sh
    FROM   annual
)
SELECT (SELECT ROUND(corr(nh, sh)::numeric, 2)     FROM annual)  AS corr_levels,
       (SELECT ROUND(corr(d_nh, d_sh)::numeric, 2) FROM changes) AS corr_year_to_year_changes;


-- A15. Median vs mean per decade (ordered-set aggregate percentile_cont)
-- WITHIN GROUP (ORDER BY ...) gives the aggregate the sorted values it needs.
-- When median and mean differ a lot, a few extreme months pull the mean.
SELECT (year / 10) * 10                                                          AS decade,
       ROUND(AVG(anomaly), 2)                                                    AS mean,
       ROUND((percentile_cont(0.5) WITHIN GROUP (ORDER BY anomaly))::numeric, 2) AS median,
       ROUND((percentile_cont(0.9) WITHIN GROUP (ORDER BY anomaly))::numeric, 2) AS p90
FROM   v_monthly
WHERE  region = 'GLB'
GROUP  BY decade
ORDER  BY decade DESC
LIMIT  6;


-- A16. Trailing 12-month mean with a RANGE window on dates
-- ROWS counts rows; RANGE uses the ORDER BY value itself: "every month whose obs_date
-- is within 11 months before this one". With a missing month, ROWS would silently reach
-- one month further back, RANGE would not.
SELECT to_char(obs_date, 'Mon YYYY') AS month,
       anomaly,
       ROUND(AVG(anomaly) OVER (ORDER BY obs_date
                                RANGE BETWEEN INTERVAL '11 months' PRECEDING AND CURRENT ROW), 2)
                                     AS trailing_12m_mean
FROM   v_monthly
WHERE  region = 'GLB'
ORDER  BY obs_date DESC
LIMIT  12;
