"""Export an analysis-ready dataset for Kaggle from the database.

Usage:
    python scripts/export_kaggle.py                  # writes data/kaggle/ (git-ignored)
    python scripts/export_kaggle.py --out some/dir

Every file comes from the same views the Playground offers, so each one can be reproduced
with SQL. Writes the CSV files, the annual grid as Parquet, the dataset description
(README.md) and Kaggle's dataset-metadata.json. Upload the folder on kaggle.com
(New Dataset) or with the Kaggle CLI; nothing is uploaded from here.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from db import ROOT, get_connection

OUT_DIR = ROOT / "data" / "kaggle"
KAGGLE_ID = "zeynepsonmeez/global-country-temperature-anomalies"
REPO_URL = "https://github.com/zeynepsonmeez/global-temperature-sql"
TREND_START = 1970                  # country trends since 1970, like the README and the map


@dataclass(frozen=True)
class Export:
    name: str                       # file name in the dataset
    sql: str
    about: str                      # one line for the dataset description
    columns: dict[str, str]         # column -> meaning, for the description


EXPORTS = [
    Export(
        "monthly_global.csv",
        "SELECT region, year, month, anomaly FROM v_monthly ORDER BY region, year, month",
        "Monthly anomaly of the globe and the two hemispheres.",
        {"region": "GLB (globe), NH or SH", "year": "year", "month": "1–12",
         "anomaly": "°C relative to 1951–1980; empty where NASA has no value"},
    ),
    Export(
        "zonal_annual.csv",
        "SELECT region AS band, year, anomaly FROM v_annual ORDER BY band, year",
        "Annual anomaly of NASA's eight latitude bands.",
        {"band": "latitude band, e.g. 64N-90N", "year": "year", "anomaly": "°C relative to 1951–1980"},
    ),
    Export(
        "country_annual.csv",
        """SELECT COALESCE(iso_a3, adm0_a3) AS iso3, country, continent, year,
                  ROUND(anomaly::numeric, 3) AS anomaly, ROUND(coverage::numeric, 3) AS coverage
           FROM   v_country_annual ORDER BY iso3, year""",
        "Annual anomaly of every country: the grid cells inside its border, weighted by overlap area.",
        {"iso3": "ISO 3166 alpha-3 code (Natural Earth code where ISO has none)", "country": "name",
         "continent": "continent", "year": "year", "anomaly": "°C relative to 1951–1980",
         "coverage": "share of the country's area with data that year (0–1); 0.9 or more is reliable"},
    ),
    Export(
        "country_trends.csv",
        """SELECT COALESCE(iso_a3, adm0_a3) AS iso3, country, continent,
                  ROUND((regr_slope(anomaly, year) * 10)::numeric, 3) AS rate_per_decade,
                  ROUND(AVG(anomaly) FILTER (WHERE year > %(end)s - 10)::numeric, 2) AS mean_last_10y,
                  COUNT(*) AS years
           FROM   v_country_annual
           WHERE  year BETWEEN %(start)s AND %(end)s AND coverage >= 0.9
           GROUP  BY iso3, country, continent
           HAVING COUNT(*) >= 0.8 * (%(end)s - %(start)s + 1)
           ORDER  BY rate_per_decade DESC""",
        "Linear warming rate of every well-covered country since 1970 (years with 90 % coverage or more).",
        {"iso3": "country code", "country": "name", "continent": "continent",
         "rate_per_decade": "least-squares trend, °C per decade",
         "mean_last_10y": "mean anomaly of the last 10 years, °C", "years": "number of years in the fit"},
    ),
    Export(
        "grid_annual.parquet",
        """SELECT g.cell_id, c.lat, c.lon, g.year, ROUND(g.anomaly::numeric, 3) AS anomaly
           FROM   v_grid_annual g JOIN grid_cells c USING (cell_id) ORDER BY g.year, g.cell_id""",
        "Annual anomaly of every 2°×2° grid cell (complete years only), for maps.",
        {"cell_id": "cell number", "lat": "cell centre latitude", "lon": "cell centre longitude",
         "year": "year", "anomaly": "°C relative to 1951–1980"},
    ),
    Export(
        "enso_oni.csv",
        "SELECT obs_date, season, oni, phase FROM v_enso ORDER BY obs_date",
        "Oceanic Niño Index (El Niño / La Niña), stored on the centre month of each 3-month season.",
        {"obs_date": "centre month", "season": "3-month season, e.g. DJF", "oni": "°C",
         "phase": "El Nino (ONI ≥ +0.5), La Nina (≤ −0.5) or Neutral"},
    ),
    Export(
        "co2_monthly.csv",
        "SELECT obs_date, co2_ppm, co2_deseason FROM v_co2 ORDER BY obs_date",
        "Monthly mean CO₂ at Mauna Loa (the Keeling curve).",
        {"obs_date": "month", "co2_ppm": "ppm", "co2_deseason": "ppm, seasonal cycle removed"},
    ),
    Export(
        "enso_adjusted.csv",
        "SELECT obs_date, observed, enso_component, adjusted FROM model_enso_adjusted ORDER BY obs_date",
        "Global monthly anomaly with the El Niño signal removed (trend + lagged ONI regression since 1970).",
        {"obs_date": "month", "observed": "global anomaly, °C", "enso_component": "part explained by ENSO, °C",
         "adjusted": "observed − enso_component, °C"},
    ),
]


def last_complete_year(cur) -> int:
    cur.execute("""SELECT MAX(year) FROM (SELECT year FROM v_monthly WHERE region = 'GLB'
                   GROUP BY year HAVING COUNT(anomaly) = 12) y""")
    return cur.fetchone()[0]


def snapshot(cur) -> tuple[str, str]:
    """NASA's release date of the loaded data and the date it was downloaded."""
    cur.execute("""SELECT source_last_modified, downloaded_at FROM datasets
                   WHERE dataset_id = (SELECT dataset_id FROM v_latest_dataset)""")
    released, downloaded = cur.fetchone()
    return f"{released:%d %b %Y}", f"{downloaded:%Y-%m-%d}"


def read(cur, sql: str, params: dict) -> pd.DataFrame:
    cur.execute(sql, params)
    return pd.DataFrame(cur.fetchall(), columns=[d.name for d in cur.description])


def description(exports: dict[str, tuple[Export, int]], first: int, last: int, released: str,
                downloaded: str) -> str:
    files = "\n".join(f"| `{e.name}` | {rows:,} | {e.about} |" for e, rows in exports.values())
    columns = "\n\n".join(
        f"**{e.name}**\n\n" + "\n".join(f"- `{col}`: {meaning}" for col, meaning in e.columns.items())
        for e, _ in exports.values()
    )
    return f"""# Global & Country Temperature Anomalies {first}–{last}

Analysis-ready temperature anomalies from NASA GISTEMP v4: the globe, the hemispheres,
latitude bands, every country and the 2°×2° grid, plus the El Niño index and Mauna Loa CO₂.
Anomalies are in °C relative to the 1951–1980 average.

The country series are not published by NASA. They were computed in PostGIS by intersecting
each 2°×2° grid cell with Natural Earth country borders and weighting the cells by their overlap
area measured on the sphere.

## Files

| File | Rows | Contents |
|---|---:|---|
{files}

## Columns

{columns}

## Method notes

- Snapshot: NASA GISTEMP release of {released}, downloaded {downloaded}. NASA revises past values
  slightly with each release.
- The grid uses NASA's 1200 km smoothing radius: small countries and islands borrow values from
  their surroundings, so their series are smoother and less certain.
- Use `coverage` in `country_annual.csv`: early years of many countries have little data.
- `enso_adjusted.csv` is a statistical association (regression), not an attribution.

## How it was made

Every file is exported by `scripts/export_kaggle.py` from a PostgreSQL + PostGIS database, with
the SQL in the script itself. Code, methods and tests: {REPO_URL}

## Sources and citation

- GISTEMP Team, {downloaded[:4]}: GISS Surface Temperature Analysis (GISTEMP), version 4. NASA Goddard
  Institute for Space Studies. https://data.giss.nasa.gov/gistemp/ (accessed {downloaded}).
- Lenssen, N. J. L. et al. (2019). Improvements in the GISTEMP uncertainty model. Journal of
  Geophysical Research: Atmospheres, 124, 6307–6326.
- Natural Earth 1:50m Admin 0 Countries, v5.1.2 (public domain). https://www.naturalearthdata.com/
- NOAA Climate Prediction Center, Oceanic Niño Index. https://www.cpc.ncep.noaa.gov/
- NOAA Global Monitoring Laboratory, Mauna Loa CO₂. https://gml.noaa.gov/ccgg/trends/

The derived files are shared under the same terms as their sources; please cite the sources above.
"""


def export(out_dir: Path = OUT_DIR, include_grid: bool = True) -> dict[str, int]:
    """Write every file into out_dir and return the number of rows per file."""
    out_dir.mkdir(parents=True, exist_ok=True)
    written: dict[str, tuple[Export, int]] = {}
    with get_connection() as conn, conn.cursor() as cur:
        last = last_complete_year(cur)
        released, downloaded = snapshot(cur)
        params = {"start": TREND_START, "end": last}
        for e in EXPORTS:
            if e.name.endswith(".parquet") and not include_grid:
                continue
            frame = read(cur, e.sql, params)
            if e.name.endswith(".parquet"):
                frame.astype({"anomaly": "float32", "lat": "float32", "lon": "float32"}) \
                     .to_parquet(out_dir / e.name, index=False)
            else:
                frame.to_csv(out_dir / e.name, index=False, lineterminator="\n")
            written[e.name] = (e, len(frame))
            print(f"OK     {e.name:<22} {len(frame):>10,} rows")
        cur.execute("SELECT MIN(year) FROM v_monthly")
        first = cur.fetchone()[0]

    (out_dir / "README.md").write_text(description(written, first, last, released, downloaded),
                                       encoding="utf-8", newline="\n")
    metadata = {
        "title": f"Global & Country Temperature Anomalies {first}-{last}",
        "subtitle": "NASA GISTEMP v4 for the globe, latitude bands, countries and the 2°×2° grid",
        "id": KAGGLE_ID,
        "licenses": [{"name": "other"}],
        "keywords": ["climate", "weather and climate", "earth and nature", "geospatial analysis"],
    }
    (out_dir / "dataset-metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
                                                   encoding="utf-8", newline="\n")
    print(f"Written to {out_dir}")
    return {name: rows for name, (_, rows) in written.items()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=OUT_DIR, help="output folder (default: data/kaggle/)")
    export(parser.parse_args().out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
