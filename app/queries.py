"""The SQL behind every chart. Parameters use psycopg's %(name)s placeholders.

These are executed with real bind parameters (never string formatting). `render()` only
produces a readable, runnable copy for the "SQL behind this chart" panel and the Playground.
"""

from __future__ import annotations

import re

from library import load_samples

# Complete-year annual means: reused by several charts.
_ANNUAL = """
    SELECT region, year, AVG(anomaly) AS anomaly
    FROM   v_monthly
    WHERE  region = %(region)s
      AND  year BETWEEN %(start)s AND %(end)s
    GROUP  BY region, year
    HAVING COUNT(anomaly) = 12"""

TREND = """-- Annual (or single-month) anomaly with a centred 5-year moving average
WITH series AS (
    SELECT region, year, AVG(anomaly) AS anomaly
    FROM   v_monthly
    WHERE  region = ANY(%(regions)s)
      AND  year BETWEEN %(start)s AND %(end)s
      AND  (%(month)s = 0 OR month = %(month)s)          -- 0 = all months (annual mean)
    GROUP  BY region, year
    HAVING COUNT(anomaly) = CASE WHEN %(month)s = 0 THEN 12 ELSE 1 END
)
SELECT region,
       year,
       ROUND(anomaly, 2) AS anomaly,
       ROUND(AVG(anomaly) OVER (PARTITION BY region ORDER BY year
                                ROWS BETWEEN 2 PRECEDING AND 2 FOLLOWING), 2) AS moving_avg_5y
FROM   series
ORDER  BY region, year;"""

HOTTEST = f"""-- The 10 hottest complete years, ranked
WITH annual AS ({_ANNUAL}
)
SELECT RANK() OVER (ORDER BY anomaly DESC) AS rank,
       year,
       ROUND(anomaly, 2) AS anomaly
FROM   annual
ORDER  BY rank, year
LIMIT  10;"""

DECADES = """-- Mean anomaly per decade and region
SELECT region,
       (year / 10) * 10       AS decade,
       ROUND(AVG(anomaly), 2) AS anomaly
FROM   v_monthly
WHERE  region = ANY(%(regions)s)
  AND  year BETWEEN %(start)s AND %(end)s
GROUP  BY region, decade
ORDER  BY region, decade;"""

HEMISPHERES = """-- Northern vs Southern Hemisphere, complete years (conditional aggregation)
SELECT year,
       ROUND(AVG(anomaly) FILTER (WHERE region = 'NH'), 2) AS nh,
       ROUND(AVG(anomaly) FILTER (WHERE region = 'SH'), 2) AS sh,
       ROUND(AVG(anomaly) FILTER (WHERE region = 'NH')
           - AVG(anomaly) FILTER (WHERE region = 'SH'), 2) AS nh_minus_sh
FROM   v_monthly
WHERE  region IN ('NH', 'SH')
  AND  year BETWEEN %(start)s AND %(end)s
GROUP  BY year
HAVING COUNT(anomaly) = 24
ORDER  BY year;"""

MONTHLY_GRID = """-- Every month of the selected period (for the heatmap)
SELECT year, month, anomaly
FROM   v_monthly
WHERE  region = %(region)s
  AND  year BETWEEN %(start)s AND %(end)s
ORDER  BY year, month;"""

MONTHLY_RATES = """-- Linear warming rate of each calendar month, in °C per decade
SELECT month,
       ROUND((regr_slope(anomaly, year) * 10)::numeric, 3) AS rate_per_decade
FROM   v_monthly
WHERE  region = %(region)s
  AND  year BETWEEN %(start)s AND %(end)s
GROUP  BY month
ORDER  BY month;"""

RECORDS = f"""-- Years warmer than every earlier year of the period (running MAX)
WITH annual AS ({_ANNUAL}
),
flagged AS (
    SELECT year,
           anomaly,
           MAX(anomaly) OVER (ORDER BY year
                              ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING) AS previous_record
    FROM   annual
)
SELECT year,
       ROUND(anomaly, 2)                                    AS anomaly,
       (previous_record IS NULL OR anomaly > previous_record) AS is_record
FROM   flagged
ORDER  BY year;"""

BANDS = """-- Warming rate and recent mean of each latitude band
SELECT r.code,
       r.name,
       r.lat_min,
       r.lat_max,
       ROUND((regr_slope(a.anomaly, a.year) * 10)::numeric, 3)        AS rate_per_decade,
       ROUND(AVG(a.anomaly) FILTER (WHERE a.year > %(end)s - 10), 2)   AS mean_last_10y
FROM   v_annual a
JOIN   regions  r ON r.code = a.region
WHERE  r.kind = 'zonal'
  AND  a.year BETWEEN %(start)s AND %(end)s
GROUP  BY r.code, r.name, r.lat_min, r.lat_max
ORDER  BY r.lat_max DESC;"""

GLOBE = """-- Mean anomaly of each latitude band over the last 10 years
SELECT r.code, r.lat_min, r.lat_max, ROUND(AVG(a.anomaly), 2) AS anomaly
FROM   v_annual a
JOIN   regions  r ON r.code = a.region
WHERE  r.kind = 'zonal'
  AND  a.year > (SELECT MAX(year) - 10 FROM v_annual)
GROUP  BY r.code, r.lat_min, r.lat_max
ORDER  BY r.lat_max DESC;"""

KPIS = f"""-- Headline numbers for one region
WITH annual AS (
    SELECT year, AVG(anomaly) AS anomaly
    FROM   v_monthly
    WHERE  region = %(region)s
    GROUP  BY year
    HAVING COUNT(anomaly) = 12
)
SELECT (SELECT year FROM annual ORDER BY year DESC LIMIT 1)                       AS latest_year,
       (SELECT ROUND(anomaly, 2) FROM annual ORDER BY year DESC LIMIT 1)          AS latest_anomaly,
       (SELECT year FROM annual ORDER BY anomaly DESC LIMIT 1)                    AS hottest_year,
       (SELECT ROUND(MAX(anomaly), 2) FROM annual)                                AS hottest_anomaly,
       (SELECT ROUND((regr_slope(anomaly, year) * 10)::numeric, 3)
        FROM annual WHERE year >= 1970)                                           AS rate_since_1970,
       (SELECT COUNT(*) FROM v_monthly
        WHERE region = %(region)s AND anomaly IS NULL)                            AS null_months;"""

FACTS = """-- Dataset coverage and version
SELECT (SELECT MIN(obs_date) FROM v_monthly)                       AS first_month,
       (SELECT MAX(obs_date) FROM v_monthly)                       AS last_month,
       d.base_period_start,
       d.base_period_end,
       d.downloaded_at,
       d.source_last_modified
FROM   datasets d
ORDER  BY d.downloaded_at DESC
LIMIT  1;"""

FINDINGS = """-- A few headline findings, all computed live
WITH annual AS (
    SELECT year, AVG(anomaly) AS anomaly
    FROM   v_monthly WHERE region = 'GLB'
    GROUP  BY year HAVING COUNT(anomaly) = 12
),
flagged AS (
    SELECT obs_date, (anomaly >= 1.0) AS hot FROM v_monthly WHERE region = 'GLB'
),
streaks AS (
    SELECT hot, COUNT(*) AS months, MAX(obs_date) AS last_month
    FROM  (SELECT obs_date, hot,
                  ROW_NUMBER() OVER (ORDER BY obs_date)
                - ROW_NUMBER() OVER (PARTITION BY hot ORDER BY obs_date) AS grp
           FROM flagged) g
    GROUP  BY hot, grp
)
SELECT (SELECT MAX(obs_date) FROM v_monthly WHERE region = 'GLB' AND anomaly < 0)   AS last_cool_month,
       (SELECT months FROM streaks WHERE hot
        ORDER BY last_month DESC LIMIT 1)                                           AS current_streak_months,
       (SELECT COUNT(*) FROM (SELECT year FROM annual ORDER BY anomaly DESC LIMIT 10) t
        WHERE year >= 2015)                                                         AS top10_since_2015;"""

# --- Spatial (PostGIS grid and countries) ------------------------------------------------

COUNTRY_RATES = """-- Warming rate of every country over the selected years (for the world map)
-- coverage >= 0.9: only years in which at least 90 percent of the country had data.
SELECT COALESCE(iso_a3, adm0_a3)                             AS iso3,
       country,
       continent,
       ROUND((regr_slope(anomaly, year) * 10)::numeric, 3)  AS rate_per_decade,
       ROUND(AVG(anomaly) FILTER (WHERE year > %(end)s - 10)::numeric, 2) AS mean_last_10y,
       COUNT(*)                                              AS years
FROM   v_country_annual
WHERE  year BETWEEN %(start)s AND %(end)s
  AND  coverage >= 0.9
GROUP  BY iso3, country, continent
HAVING COUNT(*) >= 0.8 * (%(end)s - %(start)s + 1)
ORDER  BY rate_per_decade DESC;"""

GRID_YEAR = """-- Annual mean anomaly of every 2°x2° cell in one year
SELECT g.lat, g.lon, ROUND(a.anomaly::numeric, 2) AS anomaly
FROM   v_grid_annual a
JOIN   grid_cells    g USING (cell_id)
WHERE  a.year = %(year)s;"""

GRID_YEARS = """SELECT MIN(year) AS first_year, MAX(year) AS last_year FROM v_grid_annual;"""

COUNTRY_LIST = """-- Countries with a well-covered series since 1970
SELECT adm0_a3, country
FROM   v_country_annual
WHERE  year >= 1970 AND coverage >= 0.9
GROUP  BY adm0_a3, country
HAVING COUNT(*) >= 40
ORDER  BY country;"""

# The selected countries and the global mean as one long table (UNION ALL), so one window
# function smooths every series: PARTITION BY code restarts the moving average per series.
_COMPARE_SERIES = """WITH global AS (
    SELECT year, AVG(anomaly) AS anomaly
    FROM   v_monthly
    WHERE  region = 'GLB'
    GROUP  BY year
    HAVING COUNT(anomaly) = 12
),
series AS (
    SELECT adm0_a3 AS code, country AS name, year, anomaly::numeric AS anomaly
    FROM   v_country_annual
    WHERE  adm0_a3 = ANY(%(countries)s)
    UNION ALL
    SELECT 'GLB', 'Global mean', year, anomaly
    FROM   global
)"""

COUNTRY_COMPARE = f"""-- Annual anomaly of the selected countries and the global mean, with a 5-year moving average
{_COMPARE_SERIES}
SELECT code,
       name,
       year,
       ROUND(anomaly, 2) AS anomaly,
       ROUND(AVG(anomaly) OVER (PARTITION BY code ORDER BY year
                                ROWS BETWEEN 2 PRECEDING AND 2 FOLLOWING), 2) AS moving_avg_5y
FROM   series
ORDER  BY code, year;"""

COUNTRY_COMPARE_STATS = f"""-- Warming rate since 1970 and mean of the last 10 years, per series
{_COMPARE_SERIES}
SELECT code,
       name,
       ROUND((regr_slope(anomaly, year) FILTER (WHERE year >= 1970) * 10)::numeric, 3) AS rate_since_1970,
       ROUND(AVG(anomaly) FILTER (WHERE year > (SELECT MAX(year) FROM global) - 10), 2) AS mean_last_10y
FROM   series
GROUP  BY code, name
ORDER  BY rate_since_1970 DESC;"""

# --- Climate drivers (ENSO, CO2, model outputs) ------------------------------------------------

ENSO_TEMP = """-- ONI (ENSO index) and the global monthly anomaly, side by side
SELECT e.obs_date, e.oni, e.phase, m.anomaly
FROM   v_enso e
LEFT   JOIN v_monthly m ON m.obs_date = e.obs_date AND m.region = 'GLB'
ORDER  BY e.obs_date;"""

ADJUSTED_ANNUAL = """-- Observed and ENSO-adjusted global anomaly, annual means (model output)
SELECT EXTRACT(YEAR FROM obs_date)::int AS year,
       ROUND(AVG(observed), 3)          AS observed,
       ROUND(AVG(enso_component), 3)    AS enso_part,
       ROUND(AVG(adjusted), 3)          AS adjusted
FROM   model_enso_adjusted
GROUP  BY 1
HAVING COUNT(*) = 12
ORDER  BY 1;"""

MODEL_RESULTS = """-- Every number reported by scripts/run_models.py
SELECT metric, value, ci_low, ci_high, unit, method
FROM   model_results
ORDER  BY metric;"""

BREAK_PROFILE = """-- Fit of the two-segment trend for every candidate breakpoint year
SELECT break_year, sse, slope_before, slope_after
FROM   model_breakpoints
ORDER  BY break_year;"""

ANNUAL_GLOBAL = """-- Annual global mean anomaly, complete years
SELECT year, ROUND(AVG(anomaly), 3) AS anomaly
FROM   v_monthly
WHERE  region = 'GLB'
GROUP  BY year
HAVING COUNT(anomaly) = 12
ORDER  BY year;"""

CO2_TEMP_ANNUAL = """-- Annual mean CO2 and global anomaly (1959 onwards)
SELECT m.year,
       ROUND(AVG(c.co2_ppm), 2)   AS co2_ppm,
       ROUND(AVG(m.anomaly), 3)   AS anomaly
FROM   v_monthly m
JOIN   v_co2     c ON c.obs_date = m.obs_date
WHERE  m.region = 'GLB'
GROUP  BY m.year
HAVING COUNT(*) = 12
ORDER  BY m.year;"""

CO2_MONTHLY = """-- The Keeling curve: monthly and seasonally adjusted CO2 at Mauna Loa
SELECT obs_date, co2_ppm, co2_deseason
FROM   v_co2
ORDER  BY obs_date;"""


def library(code: str) -> str:
    """The text of a query from the sql/ library (e.g. "D3"): the page runs the very same SQL."""
    return next(s.sql for s in load_samples() if s.code == code)


SCHEMA = """SELECT table_name, column_name, data_type
FROM   information_schema.columns
WHERE  table_schema = 'playground'
ORDER  BY table_name, ordinal_position;"""


def _literal(value) -> str:
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, (list, tuple)):
        return "ARRAY[" + ", ".join(_literal(v) for v in value) + "]"
    return "'" + str(value).replace("'", "''") + "'"


def render(sql: str, params: dict) -> str:
    """Return `sql` with placeholders replaced by SQL literals — for display only."""
    return re.sub(r"%\((\w+)\)s", lambda m: _literal(params[m.group(1)]), sql)
