-- GlobalTemperatureSQL — database schema (PostgreSQL 17)
-- Safe to re-run: drops and recreates every object in dependency order.

BEGIN;

DROP VIEW  IF EXISTS v_annual, v_monthly, v_latest_dataset;
DROP TABLE IF EXISTS zonal_annual_anomalies, monthly_anomalies, regions, datasets;

-- ---------------------------------------------------------------------------
-- datasets: one row per downloaded NASA snapshot (data versioning)
-- ---------------------------------------------------------------------------
CREATE TABLE datasets (
    dataset_id            SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name                  TEXT        NOT NULL,
    source_url            TEXT        NOT NULL,
    base_period_start     SMALLINT    NOT NULL,
    base_period_end       SMALLINT    NOT NULL,
    downloaded_at         TIMESTAMPTZ NOT NULL,
    source_last_modified  TIMESTAMPTZ,
    loaded_at             TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT datasets_snapshot_unique UNIQUE (name, downloaded_at),
    CONSTRAINT datasets_base_period_valid CHECK (base_period_start < base_period_end)
);

-- ---------------------------------------------------------------------------
-- regions: global, hemispheres and latitude bands
-- ---------------------------------------------------------------------------
CREATE TABLE regions (
    region_id  SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code       TEXT     NOT NULL UNIQUE,
    name       TEXT     NOT NULL,
    kind       TEXT     NOT NULL,
    lat_min    SMALLINT NOT NULL,
    lat_max    SMALLINT NOT NULL,

    CONSTRAINT regions_kind_valid
        CHECK (kind IN ('global', 'hemisphere', 'zonal_wide', 'zonal')),
    CONSTRAINT regions_lat_valid
        CHECK (lat_min BETWEEN -90 AND 90 AND lat_max BETWEEN -90 AND 90 AND lat_min < lat_max)
);

-- ---------------------------------------------------------------------------
-- monthly_anomalies: GLB, NH, SH — one row per month
-- ---------------------------------------------------------------------------
CREATE TABLE monthly_anomalies (
    dataset_id  SMALLINT     NOT NULL REFERENCES datasets (dataset_id) ON DELETE CASCADE,
    region_id   SMALLINT     NOT NULL REFERENCES regions (region_id),
    year        SMALLINT     NOT NULL,
    month       SMALLINT     NOT NULL,
    anomaly     NUMERIC(4,2),                -- NULL = missing value, never 0
    obs_date    DATE GENERATED ALWAYS AS (make_date(year, month, 1)) STORED,

    PRIMARY KEY (dataset_id, region_id, year, month),
    CONSTRAINT monthly_year_valid  CHECK (year >= 1880),
    CONSTRAINT monthly_month_valid CHECK (month BETWEEN 1 AND 12)
);

-- ---------------------------------------------------------------------------
-- zonal_annual_anomalies: latitude bands — one row per year
-- ---------------------------------------------------------------------------
CREATE TABLE zonal_annual_anomalies (
    dataset_id  SMALLINT     NOT NULL REFERENCES datasets (dataset_id) ON DELETE CASCADE,
    region_id   SMALLINT     NOT NULL REFERENCES regions (region_id),
    year        SMALLINT     NOT NULL,
    anomaly     NUMERIC(4,2),

    PRIMARY KEY (dataset_id, region_id, year),
    CONSTRAINT zonal_year_valid CHECK (year >= 1880)
);

-- ---------------------------------------------------------------------------
-- Convenience views: always the most recent snapshot, with region codes
-- ---------------------------------------------------------------------------
CREATE VIEW v_latest_dataset AS
SELECT dataset_id
FROM   datasets
ORDER  BY downloaded_at DESC
LIMIT  1;

CREATE VIEW v_monthly AS
SELECT r.code      AS region,
       m.year,
       m.month,
       m.obs_date,
       m.anomaly
FROM   monthly_anomalies m
JOIN   regions r USING (region_id)
WHERE  m.dataset_id = (SELECT dataset_id FROM v_latest_dataset);

CREATE VIEW v_annual AS
SELECT r.code      AS region,
       z.year,
       z.anomaly
FROM   zonal_annual_anomalies z
JOIN   regions r USING (region_id)
WHERE  z.dataset_id = (SELECT dataset_id FROM v_latest_dataset);

-- ---------------------------------------------------------------------------
-- Documentation stored in the database itself (visible with \d+ in psql)
-- ---------------------------------------------------------------------------
COMMENT ON TABLE  datasets IS 'One row per downloaded NASA GISTEMP v4 snapshot (see data/raw/manifest.json).';
COMMENT ON TABLE  regions IS 'Global mean, hemispheres and GISTEMP latitude bands.';
COMMENT ON COLUMN regions.code IS 'NASA column label, e.g. GLB, NH, 64N-90N.';
COMMENT ON TABLE  monthly_anomalies IS 'Monthly temperature anomalies for GLB, NH and SH.';
COMMENT ON COLUMN monthly_anomalies.anomaly IS 'Degrees Celsius relative to the 1951-1980 mean; NULL when missing.';
COMMENT ON COLUMN monthly_anomalies.obs_date IS 'First day of the month, derived from year and month.';
COMMENT ON TABLE  zonal_annual_anomalies IS 'Annual temperature anomalies for latitude bands (NASA ZonAnn).';
COMMENT ON VIEW   v_monthly IS 'Monthly anomalies of the latest snapshot, with region codes.';
COMMENT ON VIEW   v_annual IS 'Zonal annual anomalies of the latest snapshot, with region codes.';

COMMIT;
