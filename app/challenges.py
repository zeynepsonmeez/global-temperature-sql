"""Playground challenges: the user's result is compared with a reference query's result."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class Challenge:
    id: str
    topic: str
    task: dict[str, str]
    hint: dict[str, str]
    reference_sql: str
    ordered: bool = False   # True when the row order is part of the answer


_ANNUAL = """WITH annual AS (
    SELECT year, AVG(anomaly) AS anomaly
    FROM   v_monthly WHERE region = 'GLB'
    GROUP  BY year HAVING COUNT(anomaly) = 12)"""

CHALLENGES = [
    Challenge(
        "c1", "GROUP BY · HAVING",
        {"en": "List the 10 hottest complete years of the global series. Columns: year, annual mean anomaly.",
         "tr": "Küresel serinin en sıcak 10 tam yılını listeleyin. Sütunlar: yıl, yıllık ortalama anomali."},
        {"en": "GROUP BY year, keep only years with HAVING COUNT(anomaly) = 12, then ORDER BY ... DESC LIMIT 10.",
         "tr": "GROUP BY year, HAVING COUNT(anomaly) = 12 ile tam yılları bırakın, sonra ORDER BY ... DESC LIMIT 10."},
        f"{_ANNUAL} SELECT year, anomaly FROM annual ORDER BY anomaly DESC LIMIT 10",
    ),
    Challenge(
        "c2", "WHERE · BETWEEN · AVG",
        {"en": "For the global series, compute the average anomaly of each calendar month over 1991–2020. "
               "Columns: month, average anomaly (12 rows).",
         "tr": "Küresel seri için 1991–2020 döneminde her takvim ayının ortalama anomalisini hesaplayın. "
               "Sütunlar: ay, ortalama anomali (12 satır)."},
        {"en": "WHERE region = 'GLB' AND year BETWEEN 1991 AND 2020, then GROUP BY month.",
         "tr": "WHERE region = 'GLB' AND year BETWEEN 1991 AND 2020, ardından GROUP BY month."},
        "SELECT month, AVG(anomaly) FROM v_monthly WHERE region = 'GLB' "
        "AND year BETWEEN 1991 AND 2020 GROUP BY month",
    ),
    Challenge(
        "c3", "CTE · LAG",
        {"en": "For every complete global year, show the change from the previous year. "
               "Columns: year, change. (The first year has no previous year: its change is NULL.)",
         "tr": "Her tam küresel yıl için bir önceki yıla göre değişimi gösterin. "
               "Sütunlar: yıl, değişim. (İlk yılın öncesi yok: değişimi NULL.)"},
        {"en": "Compute annual means in a CTE, then anomaly - LAG(anomaly) OVER (ORDER BY year).",
         "tr": "Yıllık ortalamaları bir CTE'de hesaplayın, sonra anomaly - LAG(anomaly) OVER (ORDER BY year)."},
        f"{_ANNUAL} SELECT year, anomaly - LAG(anomaly) OVER (ORDER BY year) FROM annual",
    ),
    Challenge(
        "c4", "Window · running MAX",
        {"en": "Find every record year of the global series: complete years warmer than ALL earlier years "
               "(1880 itself does not count). One column: year.",
         "tr": "Küresel serideki tüm rekor yılları bulun: kendinden önceki TÜM yıllardan sıcak olan tam yıllar "
               "(1880 sayılmaz). Tek sütun: yıl."},
        {"en": "MAX(anomaly) OVER (ORDER BY year ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING)",
         "tr": "MAX(anomaly) OVER (ORDER BY year ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING)"},
        f"""{_ANNUAL}, flagged AS (
            SELECT year, anomaly, MAX(anomaly) OVER (ORDER BY year
                   ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING) AS previous_record
            FROM annual)
        SELECT year FROM flagged WHERE anomaly > previous_record""",
    ),
    Challenge(
        "c5", "regr_slope",
        {"en": "Warming rate since 1970 for GLB, NH and SH, in °C per decade, from complete-year annual means. "
               "Columns: region, rate.",
         "tr": "GLB, NH ve SH için 1970'ten beri ısınma hızı (°C / 10 yıl), tam yılların yıllık ortalamalarından. "
               "Sütunlar: bölge, hız."},
        {"en": "Annual means per region in a CTE, then regr_slope(anomaly, year) * 10 grouped by region.",
         "tr": "Bölge başına yıllık ortalamalar bir CTE'de, sonra bölgeye göre gruplayarak regr_slope(anomaly, year) * 10."},
        """WITH annual AS (
            SELECT region, year, AVG(anomaly) AS anomaly FROM v_monthly
            WHERE year >= 1970 GROUP BY region, year HAVING COUNT(anomaly) = 12)
        SELECT region, regr_slope(anomaly, year) * 10 FROM annual GROUP BY region""",
    ),
]


def _normalise(frame: pd.DataFrame) -> list[tuple]:
    """Rows as tuples, numbers rounded to 2 decimals, NULLs comparable."""
    rows = []
    for row in frame.itertuples(index=False, name=None):
        clean = []
        for value in row:
            if value is None or (isinstance(value, float) and pd.isna(value)):
                clean.append(None)
            elif isinstance(value, (int, float)) and not isinstance(value, bool):
                clean.append(round(float(value), 2))
            else:
                clean.append(str(value))
        rows.append(tuple(clean))
    return rows


def compare(user: pd.DataFrame, reference: pd.DataFrame, ordered: bool = False) -> tuple[bool, str, dict]:
    """Return (correct, reason_key, values). Column names are ignored; values must match."""
    if user.shape[1] != reference.shape[1]:
        return False, "pg.ch.cols", {"expected": reference.shape[1], "got": user.shape[1]}
    if len(user) != len(reference):
        return False, "pg.ch.rows", {"expected": len(reference), "got": len(user)}
    left, right = _normalise(user), _normalise(reference)
    if not ordered:
        key = lambda r: tuple((v is None, v if v is not None else "") for v in r)  # noqa: E731
        left, right = sorted(left, key=key), sorted(right, key=key)
    if left != right:
        return False, "pg.ch.values", {}
    return True, "", {}
