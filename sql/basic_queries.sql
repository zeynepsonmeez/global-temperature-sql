-- =============================================================================
-- GlobalTemperatureSQL — Basic queries
-- Topics: SELECT, WHERE, ORDER BY, LIMIT, GROUP BY, HAVING, COUNT/AVG/MIN/MAX
-- Run:    docker compose exec -T db psql -U gts_admin -d global_temperature < sql/basic_queries.sql
-- =============================================================================


-- B1. The 10 hottest months on record (global)
-- NULLS LAST: in PostgreSQL, NULL sorts as "larger than any value", so with DESC it
-- would come FIRST. Missing months must never appear as the "hottest" ones.
SELECT year, month, anomaly
FROM   v_monthly
WHERE  region = 'GLB'
ORDER  BY anomaly DESC NULLS LAST
LIMIT  10;


-- B2. The 10 hottest years (global annual mean)
-- GROUP BY collapses 12 monthly rows into one row per year.
-- HAVING filters AFTER grouping: only complete years (12 non-NULL months) are ranked,
-- otherwise the unfinished current year would be compared with full years.
-- COUNT(anomaly) counts non-NULL values only; COUNT(*) would count rows.
SELECT year,
       ROUND(AVG(anomaly), 2) AS annual_anomaly
FROM   v_monthly
WHERE  region = 'GLB'
GROUP  BY year
HAVING COUNT(anomaly) = 12
ORDER  BY annual_anomaly DESC
LIMIT  10;


-- B3. Summary statistics per region
SELECT region,
       COUNT(*)                AS months,
       COUNT(anomaly)          AS months_with_value,
       MIN(anomaly)            AS coldest_month,
       MAX(anomaly)            AS warmest_month,
       ROUND(AVG(anomaly), 3)  AS mean_anomaly
FROM   v_monthly
GROUP  BY region
ORDER  BY region;


-- B4. Decade averages (global)
-- Integer division: 1987 / 10 = 198, * 10 = 1980 → the decade label.
SELECT (year / 10) * 10              AS decade,
       COUNT(DISTINCT year)          AS years,
       ROUND(AVG(anomaly), 2)        AS mean_anomaly
FROM   v_monthly
WHERE  region = 'GLB'
GROUP  BY decade
ORDER  BY decade;


-- B5. Average anomaly by calendar month, 1995–2024 (last 30 complete years, global)
-- Anomalies remove the seasonal cycle, so this is NOT "the hottest month of the year";
-- it shows which months have departed most from their own 1951–1980 normal.
SELECT month,
       ROUND(AVG(anomaly), 2) AS mean_anomaly
FROM   v_monthly
WHERE  region = 'GLB'
  AND  year BETWEEN 1995 AND 2024
GROUP  BY month
ORDER  BY month;


-- B6. Years in which EVERY month was at least 1.0 °C above the baseline (global)
-- MIN(anomaly) >= 1.0 means even the coolest month of that year reached +1.0 °C.
SELECT year,
       MIN(anomaly)            AS coolest_month,
       ROUND(AVG(anomaly), 2)  AS annual_anomaly
FROM   v_monthly
WHERE  region = 'GLB'
GROUP  BY year
HAVING COUNT(anomaly) = 12
   AND MIN(anomaly) >= 1.0
ORDER  BY year;


-- B7. The 10 coldest years (global) — same query as B2, ascending order
SELECT year,
       ROUND(AVG(anomaly), 2) AS annual_anomaly
FROM   v_monthly
WHERE  region = 'GLB'
GROUP  BY year
HAVING COUNT(anomaly) = 12
ORDER  BY annual_anomaly ASC
LIMIT  10;


-- B8. When was the last month cooler than the 1951–1980 baseline? (global)
-- MAX() over a filtered set answers "the most recent X" without sorting everything.
SELECT MAX(obs_date)  AS last_month_below_baseline,
       COUNT(*)       AS months_below_baseline_total
FROM   v_monthly
WHERE  region = 'GLB'
  AND  anomaly < 0;


-- B9. Number of months at or above +1.0 °C, per decade (global)
-- Decades with zero such months do not appear: WHERE removes their rows before grouping.
-- (intermediate_queries.sql I4 shows how FILTER keeps zero counts visible.)
SELECT (year / 10) * 10 AS decade,
       COUNT(*)         AS months_at_or_above_1c
FROM   v_monthly
WHERE  region = 'GLB'
  AND  anomaly >= 1.0
GROUP  BY decade
ORDER  BY decade;


-- B10. Northern latitude bands (LIKE pattern matching on the regions table)
-- '%' matches any sequence of characters: '%N%' = "contains an N".
SELECT code, name, kind, lat_min, lat_max
FROM   regions
WHERE  kind IN ('zonal', 'zonal_wide')
  AND  code LIKE '%N%'
  AND  lat_min >= 0
ORDER  BY lat_max DESC, lat_min DESC;


-- B11. How many distinct years and months does each region cover? (COUNT DISTINCT)
-- COUNT(*) counts rows; COUNT(DISTINCT year) counts different years among them.
SELECT region,
       COUNT(*)              AS months,
       COUNT(DISTINCT year)  AS years,
       MIN(obs_date)         AS first_month,
       MAX(obs_date)         AS last_month
FROM   v_monthly
GROUP  BY region
ORDER  BY region;


-- B12. Every month of 2024 at or above +1.3 °C (BETWEEN on dates)
-- BETWEEN is inclusive on both ends: 2024-01-01 and 2024-12-01 are both included.
SELECT obs_date, anomaly
FROM   v_monthly
WHERE  region = 'GLB'
  AND  obs_date BETWEEN DATE '2024-01-01' AND DATE '2024-12-01'
  AND  anomaly >= 1.3
ORDER  BY obs_date;


-- B13. The 11th to 20th hottest years (LIMIT with OFFSET — paging through a ranking)
-- OFFSET 10 skips the first ten rows; the ORDER BY must be deterministic for paging to work.
SELECT year,
       ROUND(AVG(anomaly), 2) AS annual_anomaly
FROM   v_monthly
WHERE  region = 'GLB'
GROUP  BY year
HAVING COUNT(anomaly) = 12
ORDER  BY annual_anomaly DESC, year DESC
LIMIT  10 OFFSET 10;


-- B14. The same anomalies in Fahrenheit (arithmetic and column aliases)
-- An anomaly is a temperature DIFFERENCE: multiply by 1.8, do not add 32.
SELECT year,
       month,
       anomaly                    AS anomaly_c,
       ROUND(anomaly * 1.8, 2)    AS anomaly_f
FROM   v_monthly
WHERE  region = 'GLB' AND year = 2024
ORDER  BY month;


-- B15. Missing values per region (COUNT of a column vs COUNT(*), and COALESCE)
-- COUNT(anomaly) skips NULLs, so COUNT(*) - COUNT(anomaly) is the number of missing months.
-- COALESCE replaces a NULL with a fallback — here only for display.
SELECT region,
       COUNT(*) - COUNT(anomaly)                        AS missing_months,
       COALESCE(MIN(anomaly)::text, 'no data')          AS coldest_value
FROM   v_monthly
GROUP  BY region
ORDER  BY region;
