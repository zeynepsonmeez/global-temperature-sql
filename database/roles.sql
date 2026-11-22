-- GlobalTemperatureSQL — read-only role for the web app and the SQL Playground
-- Run after schema.sql, as the database owner, passing the reader password:
--   psql -v reader_password="..." -f database/roles.sql
-- Safe to re-run.
--
-- Defence in depth: the app also validates queries (app/sql_guard.py), but THIS file is
-- the real security boundary. Even a query that slipped past the validator can only
-- read a few views, cannot write, and is cut off after 3 seconds.

\set ON_ERROR_STOP on

-- 1. The role -----------------------------------------------------------------
SELECT format('CREATE ROLE gts_reader LOGIN PASSWORD %L', :'reader_password')
WHERE  NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'gts_reader') \gexec

ALTER ROLE gts_reader WITH LOGIN PASSWORD :'reader_password'
      NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION CONNECTION LIMIT 20;

-- Session defaults applied to every connection of this role.
ALTER ROLE gts_reader SET default_transaction_read_only = on;
ALTER ROLE gts_reader SET statement_timeout = '3s';
ALTER ROLE gts_reader SET idle_in_transaction_session_timeout = '10s';
ALTER ROLE gts_reader SET work_mem = '8MB';
ALTER ROLE gts_reader SET temp_file_limit = '32MB';
ALTER ROLE gts_reader SET search_path = playground, postgis;

BEGIN;

-- 2. Lock down the public schema (tables stay reachable only through views) --------
REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM gts_reader;

-- 3. A dedicated schema that exposes only what readers may see ---------------------
DROP SCHEMA IF EXISTS playground CASCADE;
CREATE SCHEMA playground;

CREATE VIEW playground.v_monthly AS SELECT * FROM public.v_monthly;
CREATE VIEW playground.v_annual  AS SELECT * FROM public.v_annual;
CREATE VIEW playground.regions   AS
    SELECT code, name, kind, lat_min, lat_max FROM public.regions;
CREATE VIEW playground.datasets  AS
    SELECT dataset_id, name, source_url, base_period_start, base_period_end,
           downloaded_at, source_last_modified
    FROM   public.datasets;

-- Spatial data (database/spatial_schema.sql). Geometry columns are included so the
-- Playground can be used to practise PostGIS functions such as ST_Area or ST_Intersects.
CREATE VIEW playground.grid_cells AS
    SELECT cell_id, lat, lon, area_weight, geom FROM public.grid_cells;
CREATE VIEW playground.v_grid AS
    SELECT cell_id, obs_date, anomaly FROM public.v_grid;
CREATE VIEW playground.countries AS
    SELECT country_id, adm0_a3, iso_a3, name, continent, geom FROM public.countries;
CREATE VIEW playground.cell_countries AS
    SELECT cell_id, country_id, overlap_km2 FROM public.cell_countries;
CREATE VIEW playground.v_grid_annual    AS SELECT * FROM public.v_grid_annual;
CREATE VIEW playground.v_grid_trends    AS SELECT * FROM public.v_grid_trends;
CREATE VIEW playground.v_country_annual AS SELECT * FROM public.v_country_annual;

-- Climate drivers and model outputs (database/drivers_schema.sql)
CREATE VIEW playground.v_enso AS SELECT * FROM public.v_enso;
CREATE VIEW playground.v_co2  AS SELECT * FROM public.v_co2;
CREATE VIEW playground.model_enso_adjusted AS SELECT * FROM public.model_enso_adjusted;
CREATE VIEW playground.model_results       AS SELECT * FROM public.model_results;
CREATE VIEW playground.model_breakpoints   AS SELECT * FROM public.model_breakpoints;

COMMENT ON SCHEMA playground IS 'Read-only views for the web app and SQL Playground.';
COMMENT ON VIEW playground.v_grid IS 'Monthly anomalies of every 2x2 degree cell (~25 million rows).';
COMMENT ON VIEW playground.v_country_annual IS 'Area-weighted annual anomaly per country.';
COMMENT ON VIEW playground.v_monthly IS 'Monthly anomalies (GLB, NH, SH), latest snapshot.';
COMMENT ON VIEW playground.v_annual  IS 'Annual anomalies of latitude bands, latest snapshot.';

-- Views run with their owner's rights, so the reader needs no access to the base tables.
GRANT USAGE  ON SCHEMA playground TO gts_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA playground TO gts_reader;
-- PostGIS types and functions only (no tables live in the postgis schema).
GRANT USAGE  ON SCHEMA postgis TO gts_reader;

-- 4. No temporary tables (CREATE TEMP would otherwise be allowed to everyone)
REVOKE TEMPORARY ON DATABASE global_temperature FROM PUBLIC;
GRANT  CONNECT   ON DATABASE global_temperature TO gts_reader;

COMMIT;
