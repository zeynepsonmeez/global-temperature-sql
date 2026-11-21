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
