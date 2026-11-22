-- GlobalTemperatureSQL — climate drivers (ENSO, CO2) and statistical model results
-- Run after schema.sql. Safe to re-run. Data: scripts/load_drivers.py, scripts/run_models.py.

BEGIN;

DROP TABLE IF EXISTS model_breakpoints, model_results, model_enso_adjusted, co2_monthly, enso_oni CASCADE;

-- ---------------------------------------------------------------------------
-- enso_oni: Oceanic Niño Index. NOAA publishes 3-month running means labelled by
-- season (DJF, JFM, ...); each value is stored on the CENTRE month (DJF -> January).
-- ---------------------------------------------------------------------------
CREATE TABLE enso_oni (
    obs_date  DATE         PRIMARY KEY,
    season    CHAR(3)      NOT NULL,
    oni       NUMERIC(4,2) NOT NULL,
    phase     TEXT GENERATED ALWAYS AS (
                  CASE WHEN oni >=  0.5 THEN 'El Nino'
                       WHEN oni <= -0.5 THEN 'La Nina'
                       ELSE 'Neutral' END) STORED,

    CONSTRAINT enso_oni_day_one CHECK (EXTRACT(DAY FROM obs_date) = 1),
    CONSTRAINT enso_oni_range   CHECK (oni BETWEEN -4 AND 4)
);

-- ---------------------------------------------------------------------------
-- co2_monthly: Mauna Loa CO2, monthly mean and seasonally adjusted (ppm)
-- ---------------------------------------------------------------------------
CREATE TABLE co2_monthly (
    obs_date        DATE         PRIMARY KEY,
    co2_ppm         NUMERIC(6,2) NOT NULL,
    co2_deseason    NUMERIC(6,2) NOT NULL,
    days_measured   SMALLINT,                    -- NULL where NOAA reports -1 (not available)

    CONSTRAINT co2_day_one CHECK (EXTRACT(DAY FROM obs_date) = 1),
    CONSTRAINT co2_range   CHECK (co2_ppm BETWEEN 250 AND 600 AND co2_deseason BETWEEN 250 AND 600)
);

-- ---------------------------------------------------------------------------
-- Model outputs written by scripts/run_models.py (see docs/METHODS.md)
-- ---------------------------------------------------------------------------
CREATE TABLE model_enso_adjusted (
    obs_date        DATE         PRIMARY KEY,
    observed        NUMERIC(5,3) NOT NULL,       -- global anomaly, °C
    enso_component  NUMERIC(5,3) NOT NULL,       -- part explained by ENSO (lagged ONI x coefficient)
    adjusted        NUMERIC(5,3) NOT NULL        -- observed - enso_component
);

CREATE TABLE model_results (
    metric     TEXT PRIMARY KEY,
    value      DOUBLE PRECISION NOT NULL,
    ci_low     DOUBLE PRECISION,
    ci_high    DOUBLE PRECISION,
    unit       TEXT,
    method     TEXT NOT NULL
);

CREATE TABLE model_breakpoints (
    break_year  SMALLINT PRIMARY KEY,
    sse         DOUBLE PRECISION NOT NULL,       -- residual sum of squares of the hinge fit
    slope_before DOUBLE PRECISION NOT NULL,      -- °C per decade
    slope_after  DOUBLE PRECISION NOT NULL
);

CREATE VIEW v_enso AS SELECT obs_date, season, oni, phase FROM enso_oni;
CREATE VIEW v_co2  AS SELECT obs_date, co2_ppm, co2_deseason FROM co2_monthly;

COMMENT ON TABLE enso_oni IS 'NOAA CPC Oceanic Nino Index; 3-month mean stored on its centre month.';
COMMENT ON COLUMN enso_oni.phase IS 'El Nino (ONI >= +0.5), La Nina (<= -0.5), otherwise Neutral (NOAA threshold, single month).';
COMMENT ON TABLE co2_monthly IS 'NOAA GML Mauna Loa monthly mean CO2 in ppm.';
COMMENT ON TABLE model_enso_adjusted IS 'Global anomaly with the linear ENSO signal removed; see docs/METHODS.md.';

COMMIT;
