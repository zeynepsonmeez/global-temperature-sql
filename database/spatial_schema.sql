-- GlobalTemperatureSQL — spatial schema: 2°x2° temperature grid, countries, PostGIS
-- Run after schema.sql. Safe to re-run: drops and recreates the spatial objects.
-- Data is loaded by scripts/load_grid.py.

-- PostGIS lives in its own schema, so the read-only role can be given the spatial
-- functions without being given access to the public schema.
CREATE SCHEMA IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis SCHEMA postgis;
DO $$ BEGIN
    EXECUTE format('ALTER DATABASE %I SET search_path = public, postgis', current_database());
END $$;
SET search_path = public, postgis;

BEGIN;

DROP MATERIALIZED VIEW IF EXISTS mv_country_annual, mv_grid_trends, mv_grid_annual CASCADE;
DROP VIEW  IF EXISTS v_grid, v_grid_annual, v_grid_trends, v_country_annual CASCADE;
DROP TABLE IF EXISTS cell_countries, countries, grid_anomalies, grid_cells CASCADE;

-- ---------------------------------------------------------------------------
-- grid_cells: the 16,200 cells of the 2°x2° grid
-- ---------------------------------------------------------------------------
CREATE TABLE grid_cells (
    cell_id      SMALLINT PRIMARY KEY,
    lat          REAL     NOT NULL,             -- centre of the cell
    lon          REAL     NOT NULL,
    area_weight  DOUBLE PRECISION NOT NULL,     -- share of the Earth's surface; all cells sum to 1
    geom         geometry(Polygon, 4326) NOT NULL,

    CONSTRAINT grid_cells_lat_valid CHECK (lat BETWEEN -90 AND 90),
    CONSTRAINT grid_cells_lon_valid CHECK (lon BETWEEN -180 AND 180),
    CONSTRAINT grid_cells_weight_valid CHECK (area_weight > 0 AND area_weight < 1)
);
CREATE INDEX grid_cells_geom_gist ON grid_cells USING gist (geom);

-- ---------------------------------------------------------------------------
-- grid_anomalies: one row per cell and month (~25 million rows)
--   * anomaly_c is the anomaly in HUNDREDTHS of a degree as SMALLINT: NASA stores the
--     grid as int16 x 0.01, so this is lossless and takes 2 bytes instead of 4–8.
--   * Column order (date, smallint, smallint) packs each row into 8 bytes with no padding.
--   * Cells without data are not stored (no NULL rows).
--   * Partitioned by decade: queries on a date range only read the matching partitions.
--   * The primary key, the foreign key to grid_cells and a BRIN index are added by
--     load_grid.py AFTER the bulk load: building/validating them once over the whole table
--     is much faster than checking 25 million rows one by one during COPY.
-- ---------------------------------------------------------------------------
CREATE TABLE grid_anomalies (
    obs_date   DATE     NOT NULL,
    cell_id    SMALLINT NOT NULL,
    anomaly_c  SMALLINT NOT NULL,

    CONSTRAINT grid_anomalies_day_one CHECK (EXTRACT(DAY FROM obs_date) = 1)
) PARTITION BY RANGE (obs_date);

DO $$
DECLARE decade int;
BEGIN
    FOR decade IN 1880..2030 BY 10 LOOP
        EXECUTE format(
            'CREATE TABLE grid_anomalies_%s PARTITION OF grid_anomalies
             FOR VALUES FROM (%L) TO (%L)',
            decade, make_date(decade, 1, 1), make_date(decade + 10, 1, 1));
    END LOOP;
END $$;

-- ---------------------------------------------------------------------------
-- countries: Natural Earth 1:50m
-- ---------------------------------------------------------------------------
CREATE TABLE countries (
    country_id  SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    adm0_a3     CHAR(3)  NOT NULL UNIQUE,       -- Natural Earth code (always set, unlike ISO_A3)
    iso_a3      CHAR(3),                        -- ISO code, NULL where Natural Earth has none
    name        TEXT     NOT NULL,
    continent   TEXT,
    geom        geometry(MultiPolygon, 4326) NOT NULL
);
CREATE INDEX countries_geom_gist ON countries USING gist (geom);

-- ---------------------------------------------------------------------------
-- cell_countries: which grid cells cover which country, and by how much
-- ---------------------------------------------------------------------------
CREATE TABLE cell_countries (
    cell_id      SMALLINT NOT NULL REFERENCES grid_cells (cell_id),
    country_id   SMALLINT NOT NULL REFERENCES countries (country_id) ON DELETE CASCADE,
    overlap_km2  REAL     NOT NULL CHECK (overlap_km2 > 0),   -- area of cell ∩ country
    PRIMARY KEY (country_id, cell_id)
);

-- ---------------------------------------------------------------------------
-- Views and materialized views
-- ---------------------------------------------------------------------------
CREATE VIEW v_grid AS
SELECT cell_id, obs_date, (anomaly_c / 100.0)::numeric(5, 2) AS anomaly
FROM   grid_anomalies;

-- Annual mean per cell (complete years only): 16,200 cells x ~146 years
CREATE MATERIALIZED VIEW mv_grid_annual AS
SELECT cell_id,
       EXTRACT(YEAR FROM obs_date)::smallint AS year,
       (AVG(anomaly_c) / 100.0)::real        AS anomaly
FROM   grid_anomalies
GROUP  BY cell_id, EXTRACT(YEAR FROM obs_date)
HAVING COUNT(*) = 12
WITH NO DATA;

-- Warming rate per cell since 1970 and its recent mean, for maps
CREATE MATERIALIZED VIEW mv_grid_trends AS
SELECT cell_id,
       (regr_slope(anomaly, year) * 10)::real                                    AS rate_per_decade,
       AVG(anomaly) FILTER (WHERE year > (SELECT MAX(year) - 10 FROM mv_grid_annual))::real AS mean_last_10y,
       COUNT(*)::smallint                                                        AS years
FROM   mv_grid_annual
WHERE  year >= 1970
GROUP  BY cell_id
HAVING COUNT(*) >= 40
WITH NO DATA;

-- Area-weighted annual mean per country. coverage = share of the country's area that had data.
CREATE MATERIALIZED VIEW mv_country_annual AS
WITH country_area AS (
    SELECT country_id, SUM(overlap_km2) AS total_km2 FROM cell_countries GROUP BY country_id
)
SELECT cc.country_id,
       g.year,
       (SUM(g.anomaly * cc.overlap_km2) / SUM(cc.overlap_km2))::real AS anomaly,
       (SUM(cc.overlap_km2) / MAX(a.total_km2))::real                AS coverage
FROM   cell_countries cc
JOIN   mv_grid_annual g USING (cell_id)
JOIN   country_area   a USING (country_id)
GROUP  BY cc.country_id, g.year
WITH NO DATA;

-- Stable query names over the materialized views (the same names exist in the
-- playground schema, so every query in sql/ runs for both the owner and the reader).
CREATE VIEW v_grid_annual AS SELECT cell_id, year, anomaly FROM mv_grid_annual;
CREATE VIEW v_grid_trends AS SELECT cell_id, rate_per_decade, mean_last_10y, years FROM mv_grid_trends;
CREATE VIEW v_country_annual AS
SELECT c.adm0_a3, c.iso_a3, c.name AS country, c.continent, m.year, m.anomaly, m.coverage
FROM   mv_country_annual m
JOIN   countries c USING (country_id);

CREATE UNIQUE INDEX mv_grid_annual_key    ON mv_grid_annual (cell_id, year);
CREATE INDEX        mv_grid_annual_year   ON mv_grid_annual (year);
CREATE UNIQUE INDEX mv_grid_trends_key    ON mv_grid_trends (cell_id);
CREATE UNIQUE INDEX mv_country_annual_key ON mv_country_annual (country_id, year);

COMMENT ON TABLE  grid_anomalies IS 'GISTEMP v4 2x2 degree monthly anomalies (1200 km smoothing), partitioned by decade.';
COMMENT ON COLUMN grid_anomalies.anomaly_c IS 'Anomaly in hundredths of a degree C (lossless copy of NASA int16 data). Use v_grid for degrees.';
COMMENT ON TABLE  grid_cells IS '2x2 degree cells with polygon geometry and area weight.';
COMMENT ON TABLE  countries IS 'Natural Earth 1:50m countries (v5.1.2).';
COMMENT ON TABLE  cell_countries IS 'Intersection of grid cells and countries, with overlap area in km2.';
COMMENT ON MATERIALIZED VIEW mv_country_annual IS 'Area-weighted annual anomaly per country; refreshed by load_grid.py.';

COMMIT;
