"""The SQL behind every chart. Parameters use psycopg's %(name)s placeholders.

These are executed with real bind parameters (never string formatting). `render()` only
produces a readable, runnable copy for the "SQL behind this chart" panel and the Playground.
"""

from __future__ import annotations

import re

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
