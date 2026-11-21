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
