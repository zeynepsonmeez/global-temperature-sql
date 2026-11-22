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
         "tr": "Bölge başına yıllık ortalamalar bir CTE'de, sonra bölgeye göre gruplayarak "
               "regr_slope(anomaly, year) * 10."},
        """WITH annual AS (
            SELECT region, year, AVG(anomaly) AS anomaly FROM v_monthly
            WHERE year >= 1970 GROUP BY region, year HAVING COUNT(anomaly) = 12)
        SELECT region, regr_slope(anomaly, year) * 10 FROM annual GROUP BY region""",
    ),
    Challenge(
        "c6", "WHERE · ORDER BY · LIMIT",
        {"en": "The 5 warmest months of 2024 in the global series. Columns: month, anomaly.",
         "tr": "Küresel seride 2024'ün en sıcak 5 ayı. Sütunlar: ay, anomali."},
        {"en": "Filter region and year, sort by anomaly descending, keep 5 rows.",
         "tr": "Bölge ve yılı filtreleyin, anomaliye göre azalan sıralayın, 5 satır bırakın."},
        "SELECT month, anomaly FROM v_monthly WHERE region = 'GLB' AND year = 2024 "
        "ORDER BY anomaly DESC LIMIT 5",
    ),
    Challenge(
        "c7", "COUNT · GROUP BY",
        {"en": "For each region, how many months reached at least +1.0 °C? Columns: region, months.",
         "tr": "Her bölgede kaç ay en az +1.0 °C'ye ulaştı? Sütunlar: bölge, ay sayısı."},
        {"en": "Filter with WHERE anomaly >= 1.0 first, then GROUP BY region and COUNT(*).",
         "tr": "Önce WHERE anomaly >= 1.0 ile filtreleyin, sonra GROUP BY region ve COUNT(*)."},
        "SELECT region, COUNT(*) FROM v_monthly WHERE anomaly >= 1.0 GROUP BY region",
    ),
    Challenge(
        "c8", "JOIN",
        {"en": "The anomaly of each of the 8 narrow latitude bands in 2025, with the band's NAME. "
               "Join v_annual with regions (kind = 'zonal'). Columns: name, anomaly.",
         "tr": "8 dar enlem bandının 2025 anomalisi, bandın ADIYLA birlikte. v_annual'ı regions ile "
               "birleştirin (kind = 'zonal'). Sütunlar: ad, anomali."},
        {"en": "JOIN regions r ON r.code = a.region, then filter r.kind and a.year.",
         "tr": "JOIN regions r ON r.code = a.region, sonra r.kind ve a.year ile filtreleyin."},
        "SELECT r.name, a.anomaly FROM v_annual a JOIN regions r ON r.code = a.region "
        "WHERE r.kind = 'zonal' AND a.year = 2025",
    ),
    Challenge(
        "c9", "CASE WHEN",
        {"en": "Label every complete global year 'cool' (below 0), 'mild' (0 up to 0.5) or 'warm' "
               "(0.5 and above), then count the years per label. Columns: label, years.",
         "tr": "Her tam küresel yılı 'cool' (0'ın altı), 'mild' (0 ile 0.5 arası) ya da 'warm' "
               "(0.5 ve üzeri) olarak etiketleyin, sonra etiket başına yılları sayın. Sütunlar: etiket, yıl sayısı."},
        {"en": "Annual means in a CTE; CASE WHEN anomaly < 0 THEN 'cool' WHEN anomaly < 0.5 THEN 'mild' "
               "ELSE 'warm' END.",
         "tr": "Yıllık ortalamalar bir CTE'de; CASE WHEN anomaly < 0 THEN 'cool' WHEN anomaly < 0.5 THEN 'mild' "
               "ELSE 'warm' END."},
        f"""{_ANNUAL}
        SELECT CASE WHEN anomaly < 0 THEN 'cool' WHEN anomaly < 0.5 THEN 'mild' ELSE 'warm' END AS label,
               COUNT(*)
        FROM annual GROUP BY label""",
    ),
    Challenge(
        "c10", "Subquery",
        {"en": "Every global month warmer than the warmest month BEFORE 2015. Columns: year, month.",
         "tr": "2015'TEN ÖNCEKİ en sıcak aydan daha sıcak olan bütün küresel aylar. Sütunlar: yıl, ay."},
        {"en": "WHERE anomaly > (SELECT MAX(anomaly) FROM v_monthly WHERE region = 'GLB' AND year < 2015)",
         "tr": "WHERE anomaly > (SELECT MAX(anomaly) FROM v_monthly WHERE region = 'GLB' AND year < 2015)"},
        """SELECT year, month FROM v_monthly
        WHERE region = 'GLB'
          AND anomaly > (SELECT MAX(anomaly) FROM v_monthly WHERE region = 'GLB' AND year < 2015)""",
    ),
    Challenge(
        "c11", "LAG · decades",
        {"en": "The change of the global decade mean from the previous decade (all months of each decade). "
               "Columns: decade, change — NULL for the first decade.",
         "tr": "Küresel on yıllık ortalamanın bir önceki on yıla göre değişimi (her on yılın tüm ayları). "
               "Sütunlar: on yıl, değişim — ilk on yıl için NULL."},
        {"en": "Decade = (year / 10) * 10; AVG per decade in a CTE, then mean - LAG(mean) OVER (ORDER BY decade).",
         "tr": "On yıl = (year / 10) * 10; on yıl başına AVG bir CTE'de, sonra ortalama - LAG(ortalama) "
               "OVER (ORDER BY decade)."},
        """WITH d AS (SELECT (year / 10) * 10 AS decade, AVG(anomaly) AS mean
                   FROM v_monthly WHERE region = 'GLB' GROUP BY decade)
        SELECT decade, mean - LAG(mean) OVER (ORDER BY decade) FROM d""",
    ),
    Challenge(
        "c12", "ROW_NUMBER · PARTITION BY",
        {"en": "The single warmest month of each year from 2020 to 2025 (global). Columns: year, month.",
         "tr": "2020'den 2025'e kadar her yılın en sıcak ayı (küresel). Sütunlar: yıl, ay."},
        {"en": "ROW_NUMBER() OVER (PARTITION BY year ORDER BY anomaly DESC), keep row 1.",
         "tr": "ROW_NUMBER() OVER (PARTITION BY year ORDER BY anomaly DESC), 1. satırı bırakın."},
        """WITH r AS (SELECT year, month,
                          ROW_NUMBER() OVER (PARTITION BY year ORDER BY anomaly DESC) AS rn
                   FROM v_monthly WHERE region = 'GLB' AND year BETWEEN 2020 AND 2025)
        SELECT year, month FROM r WHERE rn = 1""",
    ),
    Challenge(
        "c13", "Spatial join",
        {"en": "How many grid cells overlap Türkiye, Germany and Brazil (adm0_a3 'TUR', 'DEU', 'BRA')? "
               "Columns: adm0_a3, cells.",
         "tr": "Türkiye, Almanya ve Brezilya ile kaç ızgara hücresi örtüşüyor (adm0_a3 'TUR', 'DEU', 'BRA')? "
               "Sütunlar: adm0_a3, hücre sayısı."},
        {"en": "cell_countries holds one row per cell and country; join countries USING (country_id).",
         "tr": "cell_countries her hücre ve ülke için bir satır tutar; countries ile USING (country_id) birleştirin."},
        "SELECT c.adm0_a3, COUNT(*) FROM cell_countries cc JOIN countries c USING (country_id) "
        "WHERE c.adm0_a3 IN ('TUR', 'DEU', 'BRA') GROUP BY c.adm0_a3",
    ),
    Challenge(
        "c14", "ENSO · AVG",
        {"en": "The mean ONI of each ENSO phase in v_enso. Columns: phase, mean ONI.",
         "tr": "v_enso'daki her ENSO fazının ortalama ONI değeri. Sütunlar: faz, ortalama ONI."},
        {"en": "v_enso already has a phase column: GROUP BY phase.",
         "tr": "v_enso'da hazır bir phase sütunu var: GROUP BY phase."},
        "SELECT phase, AVG(oni) FROM v_enso GROUP BY phase",
    ),
    Challenge(
        "c15", "Window · moving average",
        {"en": "The centred 5-year moving average of the global annual mean, reported for 2010–2020. The "
               "average must use the neighbouring years even outside that range. Columns: year, moving average.",
         "tr": "Küresel yıllık ortalamanın 5 yıllık merkezli hareketli ortalaması, 2010–2020 için. Ortalama, bu "
               "aralığın dışındaki komşu yılları da kullanmalı. Sütunlar: yıl, hareketli ortalama."},
        {"en": "Compute the window over ALL years first (a CTE), filter 2010–2020 afterwards: a WHERE in the "
               "same query would run before the window and cut the neighbours off.",
         "tr": "Pencereyi önce TÜM yıllar üzerinde hesaplayın (bir CTE), 2010–2020 filtresini sonra uygulayın: "
               "aynı sorgudaki WHERE pencereden önce çalışır ve komşu yılları keser."},
        f"""{_ANNUAL},
        smoothed AS (SELECT year, AVG(anomaly) OVER (ORDER BY year ROWS BETWEEN 2 PRECEDING AND 2 FOLLOWING) AS ma
                     FROM annual)
        SELECT year, ma FROM smoothed WHERE year BETWEEN 2010 AND 2020""",
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
