-- =============================================================================
-- GlobalTemperatureSQL — Spatial queries (PostGIS, 2°x2° grid, countries)
-- Topics: spatial joins, ST_Contains, KNN (<->), ST_Area on geography, area weighting,
--         DISTINCT ON, large-table aggregation over a partitioned table
-- Objects: v_grid (~25M rows), grid_cells, countries, cell_countries,
--          v_grid_annual, v_grid_trends, v_country_annual
-- =============================================================================


-- S1. The 10 fastest-warming countries since 1970 (regression on country series)
-- coverage >= 0.9 keeps only years in which at least 90% of the country had data;
-- countries smaller than one grid cell are excluded because one cell then decides everything.
SELECT country,
       ROUND((regr_slope(anomaly, year) * 10)::numeric, 3) AS rate_per_decade,
       COUNT(*)                                            AS years
FROM   v_country_annual
WHERE  year >= 1970
  AND  coverage >= 0.9
  AND  adm0_a3 IN (SELECT c.adm0_a3
                   FROM   countries c JOIN cell_countries cc USING (country_id)
                   GROUP  BY c.adm0_a3
                   HAVING SUM(cc.overlap_km2) > 50000)
GROUP  BY country
HAVING COUNT(*) >= 50
ORDER  BY rate_per_decade DESC
LIMIT  10;


-- S2. Türkiye vs the world, last 10 complete years (JOIN of the country and global series)
SELECT t.year,
       ROUND(t.anomaly::numeric, 2) AS turkiye,
       ROUND(g.anomaly, 2)          AS global,
       ROUND((t.anomaly - g.anomaly)::numeric, 2) AS difference
FROM   v_country_annual t
JOIN  (SELECT year, AVG(anomaly) AS anomaly
       FROM   v_monthly WHERE region = 'GLB'
       GROUP  BY year HAVING COUNT(anomaly) = 12) g USING (year)
WHERE  t.adm0_a3 = 'TUR'
ORDER  BY t.year DESC
LIMIT  10;


-- S3. Which grid cells cover Türkiye, and how much of each? (spatial join result)
-- overlap_km2 = ST_Area(ST_Intersection(cell, country)::geography): measured on the sphere,
-- so a 2°x2° cell is ~49,000 km2 near the equator but much smaller near the poles.
SELECT g.cell_id,
       g.lat,
       g.lon,
       ROUND(cc.overlap_km2::numeric)                                          AS overlap_km2,
       ROUND((100 * cc.overlap_km2 / (ST_Area(g.geom::geography) / 1e6))::numeric, 1) AS pct_of_cell_in_country
FROM   cell_countries cc
JOIN   grid_cells     g USING (cell_id)
JOIN   countries      c USING (country_id)
WHERE  c.adm0_a3 = 'TUR'
ORDER  BY cc.overlap_km2 DESC
LIMIT  10;


-- S4. The grid cell that contains Istanbul, and its last 12 months (ST_Contains)
-- ST_MakePoint takes (longitude, latitude) — x before y.
WITH istanbul AS (
    SELECT cell_id
    FROM   grid_cells
    WHERE  ST_Contains(geom, ST_SetSRID(ST_MakePoint(28.98, 41.01), 4326))
)
SELECT v.obs_date, v.anomaly
FROM   v_grid v
JOIN   istanbul USING (cell_id)
WHERE  v.obs_date > (SELECT MAX(m.obs_date) FROM v_monthly m) - INTERVAL '12 months'
ORDER  BY v.obs_date;


-- S5. The 5 grid cells closest to Ankara (KNN with the <-> distance operator)
-- ORDER BY geom <-> point uses the GiST index to find nearest neighbours without
-- measuring the distance to all 16,200 cells.
SELECT cell_id,
       lat,
       lon,
       ROUND((ST_Distance(ST_Centroid(geom)::geography,
                          ST_SetSRID(ST_MakePoint(32.86, 39.93), 4326)::geography) / 1000)::numeric) AS km_from_ankara
FROM   grid_cells
ORDER  BY geom <-> ST_SetSRID(ST_MakePoint(32.86, 39.93), 4326)
LIMIT  5;


-- S6. Land vs ocean warming since 1970 (EXISTS on the spatial join)
-- A cell counts as "land" if it overlaps any country. Averages are area-weighted.
SELECT CASE WHEN EXISTS (SELECT 1 FROM cell_countries cc WHERE cc.cell_id = t.cell_id)
            THEN 'land' ELSE 'ocean' END                                   AS surface,
       COUNT(*)                                                            AS cells,
       ROUND((SUM(t.rate_per_decade * g.area_weight) / SUM(g.area_weight))::numeric, 3) AS rate_per_decade
FROM   v_grid_trends t
JOIN   grid_cells    g USING (cell_id)
GROUP  BY surface
ORDER  BY surface;


-- S7. Warming rate by continent since 1970 (area-weighted over the continent's cells)
WITH continent_cells AS (
    SELECT c.continent, cc.cell_id, SUM(cc.overlap_km2) AS km2
    FROM   cell_countries cc
    JOIN   countries      c USING (country_id)
    WHERE  c.continent NOT IN ('Seven seas (open ocean)')
    GROUP  BY c.continent, cc.cell_id
)
SELECT cc.continent,
       ROUND((SUM(t.rate_per_decade * cc.km2) / SUM(cc.km2))::numeric, 3) AS rate_per_decade,
       ROUND((SUM(cc.km2) / 1e6)::numeric, 1)                              AS million_km2
FROM   continent_cells cc
JOIN   v_grid_trends   t USING (cell_id)
GROUP  BY cc.continent
ORDER  BY rate_per_decade DESC;


-- S8. Hottest spots of the latest month, with the country each mostly lies in (DISTINCT ON)
-- DISTINCT ON (cell_id) + ORDER BY overlap DESC keeps one country per cell: the largest one.
WITH latest AS (
    SELECT cell_id, anomaly
    FROM   v_grid
    WHERE  obs_date = (SELECT MAX(m.obs_date) FROM v_monthly m)
    ORDER  BY anomaly DESC
    LIMIT  10
),
main_country AS (
    SELECT DISTINCT ON (cc.cell_id) cc.cell_id, c.name
    FROM   cell_countries cc
    JOIN   countries c USING (country_id)
    WHERE  cc.cell_id IN (SELECT l.cell_id FROM latest l)
    ORDER  BY cc.cell_id ASC, cc.overlap_km2 DESC
)
SELECT g.lat, g.lon, l.anomaly, COALESCE(m.name, '(ocean)') AS country
FROM   latest l
JOIN   grid_cells g USING (cell_id)
LEFT   JOIN main_country m USING (cell_id)
ORDER  BY l.anomaly DESC;


-- S9. How observation coverage grew: share of the Earth's surface with data, per decade
-- Area-weighted, so a polar cell counts for much less than an equatorial one.
SELECT (a.year / 10) * 10                                    AS decade,
       ROUND((100 * SUM(g.area_weight) / COUNT(DISTINCT a.year))::numeric, 1) AS pct_of_earth_with_data
FROM   v_grid_annual a
JOIN   grid_cells    g USING (cell_id)
GROUP  BY decade
ORDER  BY decade;


-- S10. Does the grid reproduce NASA's global series? (area-weighted mean vs official)
-- This is the validation run by load_grid.py, shown here for the last 10 complete years.
WITH grid AS (
    SELECT a.year, SUM(a.anomaly * g.area_weight) / SUM(g.area_weight) AS anomaly
    FROM   v_grid_annual a JOIN grid_cells g USING (cell_id)
    GROUP  BY a.year
),
official AS (
    SELECT year, AVG(anomaly) AS anomaly
    FROM   v_monthly WHERE region = 'GLB'
    GROUP  BY year HAVING COUNT(anomaly) = 12
)
SELECT o.year,
       ROUND(o.anomaly, 2)                         AS official,
       ROUND(g.anomaly::numeric, 2)                AS from_grid,
       ROUND((g.anomaly - o.anomaly)::numeric, 3)  AS difference
FROM   official o JOIN grid g USING (year)
ORDER  BY o.year DESC
LIMIT  10;


-- S11. Grid cells within 500 km of Istanbul, and their mean anomaly in 2025 (ST_DWithin)
-- ST_DWithin on geography measures real distance in metres on the sphere and can use an index.
SELECT g.cell_id,
       g.lat,
       g.lon,
       ROUND((ST_Distance(ST_Centroid(g.geom)::geography,
                          ST_SetSRID(ST_MakePoint(28.98, 41.01), 4326)::geography) / 1000)::numeric) AS km,
       ROUND(a.anomaly::numeric, 2) AS anomaly_2025
FROM   grid_cells g
JOIN   v_grid_annual a ON a.cell_id = g.cell_id AND a.year = 2025
WHERE  ST_DWithin(ST_Centroid(g.geom)::geography,
                  ST_SetSRID(ST_MakePoint(28.98, 41.01), 4326)::geography, 500000)
ORDER  BY km;


-- S12. How much of each latitude band is land? (area-weighted share of cells over countries)
-- The Northern Hemisphere bands are far more "land" — one reason they warm faster.
WITH land AS (
    SELECT cc.cell_id, LEAST(SUM(cc.overlap_km2) / (ST_Area(MAX(g.geom)::geography) / 1e6), 1) AS share
    FROM   cell_countries cc
    JOIN   grid_cells g USING (cell_id)
    GROUP  BY cc.cell_id
)
SELECT r.code,
       ROUND((100 * SUM(COALESCE(l.share, 0) * g.area_weight) / SUM(g.area_weight))::numeric, 1) AS land_pct
FROM   regions r
JOIN   grid_cells g ON g.lat BETWEEN r.lat_min AND r.lat_max
LEFT   JOIN land l USING (cell_id)
WHERE  r.kind = 'zonal'
GROUP  BY r.code, r.lat_max
ORDER  BY r.lat_max DESC;


-- S13. The largest country of each continent (ROW_NUMBER over ST_Area)
SELECT continent, name, ROUND(area_km2) AS area_km2
FROM  (SELECT continent,
              name,
              ST_Area(geom::geography) / 1e6 AS area_km2,
              ROW_NUMBER() OVER (PARTITION BY continent ORDER BY ST_Area(geom::geography) DESC) AS rn
       FROM   countries
       WHERE  continent <> 'Seven seas (open ocean)') ranked
WHERE  rn = 1
ORDER  BY area_km2 DESC;
