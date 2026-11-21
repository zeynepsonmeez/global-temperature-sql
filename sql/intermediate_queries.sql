-- =============================================================================
-- GlobalTemperatureSQL — Intermediate queries
-- Topics: CTE (WITH), JOIN, self-join, subqueries, CASE WHEN, FILTER
-- Run:    docker compose exec -T db psql -U gts_admin -d global_temperature < sql/intermediate_queries.sql
-- =============================================================================


-- I1. Northern vs Southern Hemisphere, last 10 complete years (CTE + self-join)
-- The CTE computes annual means once; the query then joins the CTE with itself:
-- "n" is the NH row and "s" is the SH row of the same year.
WITH annual AS (
    SELECT region, year, AVG(anomaly) AS anomaly
    FROM   v_monthly
    WHERE  region IN ('NH', 'SH')
    GROUP  BY region, year
    HAVING COUNT(anomaly) = 12
)
SELECT n.year,
       ROUND(n.anomaly, 2)              AS nh,
       ROUND(s.anomaly, 2)              AS sh,
       ROUND(n.anomaly - s.anomaly, 2)  AS nh_minus_sh
FROM   annual n
JOIN   annual s ON s.year = n.year AND s.region = 'SH'
WHERE  n.region = 'NH'
ORDER  BY n.year DESC
LIMIT  10;


-- I2. The same comparison per decade, without a join (conditional aggregation)
-- FILTER (WHERE ...) restricts each aggregate to some rows — one pass over the data.
-- Same idea as I1, different technique: often simpler and faster than a self-join.
SELECT (year / 10) * 10                                         AS decade,
       ROUND(AVG(anomaly) FILTER (WHERE region = 'NH'), 2)      AS nh,
       ROUND(AVG(anomaly) FILTER (WHERE region = 'SH'), 2)      AS sh,
       ROUND(AVG(anomaly) FILTER (WHERE region = 'NH')
           - AVG(anomaly) FILTER (WHERE region = 'SH'), 2)      AS nh_minus_sh
FROM   v_monthly
WHERE  region IN ('NH', 'SH')
GROUP  BY decade
ORDER  BY decade;


-- I3. Years warmer than 2016 — the record year of the 2010s (scalar subquery)
-- The inner query returns ONE value, which the outer HAVING compares against.
SELECT year,
       ROUND(AVG(anomaly), 2) AS annual_anomaly
FROM   v_monthly
WHERE  region = 'GLB'
GROUP  BY year
HAVING COUNT(anomaly) = 12
   AND AVG(anomaly) > (
        SELECT AVG(anomaly)
        FROM   v_monthly
        WHERE  region = 'GLB' AND year = 2016
   )
ORDER  BY year;


-- I4. How often were years cold, normal or warm, by period? (CASE WHEN + FILTER)
-- CASE assigns each year to a category; FILTER counts the categories per period.
WITH annual AS (
    SELECT year, AVG(anomaly) AS anomaly
    FROM   v_monthly
    WHERE  region = 'GLB'
    GROUP  BY year
    HAVING COUNT(anomaly) = 12
),
labelled AS (
    SELECT year,
           CASE
               WHEN year < 1950 THEN '1880-1949'
               WHEN year < 2000 THEN '1950-1999'
               ELSE                  '2000-'
           END AS period,
           CASE
               WHEN anomaly <  -0.2 THEN 'cool'
               WHEN anomaly <   0.2 THEN 'near baseline'
               WHEN anomaly <   0.6 THEN 'warm'
               WHEN anomaly <   1.0 THEN 'very warm'
               ELSE                      'extreme'
           END AS category
    FROM   annual
)
SELECT period,
       COUNT(*)                                          AS years,
       COUNT(*) FILTER (WHERE category = 'cool')          AS cool,
       COUNT(*) FILTER (WHERE category = 'near baseline') AS near_baseline,
       COUNT(*) FILTER (WHERE category = 'warm')          AS warm,
       COUNT(*) FILTER (WHERE category = 'very warm')     AS very_warm,
       COUNT(*) FILTER (WHERE category = 'extreme')       AS extreme
FROM   labelled
GROUP  BY period
ORDER  BY period;


-- I5. Warming by latitude band, last 10 years (JOIN with the regions table)
-- This is the query behind the globe on the home page: v_annual holds the values,
-- regions holds the latitude bounds used to order the bands from north to south.
SELECT r.code,
       r.name,
       r.lat_min,
       r.lat_max,
       ROUND(AVG(a.anomaly), 2) AS mean_anomaly_last_10y
FROM   v_annual a
JOIN   regions  r ON r.code = a.region
WHERE  r.kind = 'zonal'
  AND  a.year > (SELECT MAX(year) - 10 FROM v_annual)
GROUP  BY r.code, r.name, r.lat_min, r.lat_max
ORDER  BY r.lat_max DESC;


-- I6. Years with at least one month at or above +1.0 °C (EXISTS + correlated subquery)
-- A correlated subquery refers to the outer row (y.year) and is evaluated per row.
-- EXISTS stops at the first matching month, so it never counts more than needed.
SELECT y.year,
       (SELECT COUNT(*)
        FROM   v_monthly m
        WHERE  m.region = 'GLB' AND m.year = y.year AND m.anomaly >= 1.0) AS months_at_or_above_1c
FROM  (SELECT DISTINCT year FROM v_monthly WHERE region = 'GLB') y
WHERE  EXISTS (
        SELECT 1
        FROM   v_monthly m
        WHERE  m.region = 'GLB' AND m.year = y.year AND m.anomaly >= 1.0
       )
ORDER  BY y.year;


-- I7. The 5 hottest and 5 coldest years in one list (UNION ALL)
-- Each branch needs its own parentheses to carry its own ORDER BY / LIMIT.
-- UNION ALL keeps every row; UNION would also remove duplicates (extra work).
WITH annual AS (
    SELECT year, ROUND(AVG(anomaly), 2) AS anomaly
    FROM   v_monthly
    WHERE  region = 'GLB'
    GROUP  BY year
    HAVING COUNT(anomaly) = 12
)
(SELECT 'hottest' AS list, year, anomaly FROM annual ORDER BY anomaly DESC LIMIT 5)
UNION ALL
(SELECT 'coldest' AS list, year, anomaly FROM annual ORDER BY anomaly ASC  LIMIT 5);


-- I8. Which regions have monthly data, which only annual? (LEFT JOIN + COALESCE)
-- LEFT JOIN keeps every region even without a match; COALESCE turns the NULL count into 0.
-- Counts are aggregated BEFORE joining: joining both raw tables first would multiply rows
-- (every monthly row x every annual row of a region) and inflate the counts.
SELECT r.code,
       r.kind,
       COALESCE(m.n, 0) AS monthly_rows,
       COALESCE(a.n, 0) AS annual_rows
FROM   regions r
LEFT   JOIN (SELECT region, COUNT(*) AS n FROM v_monthly GROUP BY region) m ON m.region = r.code
LEFT   JOIN (SELECT region, COUNT(*) AS n FROM v_annual  GROUP BY region) a ON a.region = r.code
ORDER  BY r.lat_max DESC, r.lat_min DESC;


-- I9. Re-baselining: recent years relative to 1880–1900 instead of 1951–1980
-- Subtracting the mean of another period moves the zero point; trends do not change.
-- 1880–1900 is only a proxy for "pre-industrial": the IPCC uses 1850–1900, which
-- GISTEMP does not cover. One year above 1.5 °C is also not the same as passing the
-- Paris Agreement limit, which refers to a ~20-year average.
WITH annual AS (
    SELECT year, AVG(anomaly) AS anomaly
    FROM   v_monthly
    WHERE  region = 'GLB'
    GROUP  BY year
    HAVING COUNT(anomaly) = 12
),
early AS (
    SELECT AVG(anomaly) AS mean_1880_1900
    FROM   annual
    WHERE  year BETWEEN 1880 AND 1900
)
SELECT a.year,
       ROUND(a.anomaly, 2)                     AS vs_1951_1980,
       ROUND(a.anomaly - e.mean_1880_1900, 2)  AS vs_1880_1900
FROM   annual a
CROSS  JOIN early e
WHERE  a.year >= 2015
ORDER  BY a.year;


-- I10. Winter (DJF) means computed in SQL — December belongs to the NEXT year's winter
-- CASE shifts December forward one year, so Dec 2025 + Jan/Feb 2026 = winter 2026.
-- This reproduces NASA's DJF column (e.g. 2026: (1.05 + 1.08 + 1.23) / 3 = 1.12).
SELECT CASE WHEN month = 12 THEN year + 1 ELSE year END AS winter,
       ROUND(AVG(anomaly), 2)                            AS djf_anomaly
FROM   v_monthly
WHERE  region = 'GLB'
  AND  month IN (12, 1, 2)
GROUP  BY winter
HAVING COUNT(anomaly) = 3
ORDER  BY winter DESC
LIMIT  5;


-- I11. The most recent 12 months per region (date arithmetic with INTERVAL)
-- Works on obs_date, so it always uses the latest published data without hard-coded years.
SELECT region,
       to_char(MIN(obs_date), 'Mon YYYY') AS from_month,
       to_char(MAX(obs_date), 'Mon YYYY') AS to_month,
       ROUND(AVG(anomaly), 2)             AS last_12_months
FROM   v_monthly
WHERE  obs_date > (SELECT MAX(obs_date) FROM v_monthly) - INTERVAL '12 months'
GROUP  BY region
ORDER  BY region;
