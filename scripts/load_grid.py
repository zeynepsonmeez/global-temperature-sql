"""Load the 2°x2° GISTEMP grid and Natural Earth countries into PostGIS.

Usage:
    python scripts/load_grid.py                   # full record (~25 million rows, a few minutes)
    python scripts/load_grid.py --start-year 2015 # a small subset, e.g. for CI

Requires database/spatial_schema.sql and the files from download_grid.py.
Runs in ONE transaction: on any error nothing is changed. Re-running replaces the data.

Steps
  1. grid_cells      16,200 cells generated in SQL, checked against the NetCDF coordinates
  2. grid_anomalies  bulk COPY, month by month, ordered by date (good for the BRIN index)
  3. constraints     primary key, foreign key and BRIN index built once, after the load
  4. countries       Natural Earth GeoJSON -> valid MultiPolygons
  5. cell_countries  spatial join with the overlap area of every cell and country
  6. materialized views refreshed, statistics updated, global mean validated
"""

from __future__ import annotations

import argparse
import gzip
import io
import json
import shutil
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from db import get_connection
from download_grid import GRID_DIR

NC_GZ = GRID_DIR / "gistemp1200_GHCNv4_ERSSTv5.nc.gz"
NC = GRID_DIR / "gistemp1200_GHCNv4_ERSSTv5.nc"
COUNTRIES = GRID_DIR / "ne_50m_admin_0_countries.geojson"
DATASET_NAME = "GISTEMP v4 grid (1200 km)"
FILL = 32767          # NASA's int16 missing-value marker
CHUNK_MONTHS = 60


def step(label: str):
    print(f"...    {label}", flush=True)
    return time.perf_counter()


def done(started: float, detail: str = "") -> None:
    print(f"OK     {detail} ({time.perf_counter() - started:,.1f} s)", flush=True)


@contextmanager
def open_grid(path=NC_GZ):
    """Unpack the .nc.gz to a temporary file (deleted afterwards) and open it.

    The unpacked file is ~55 MB, twice the download, so it is never kept in the project.
    mask_and_scale=False keeps NASA's raw int16 hundredths: exact, no float rounding.
    """
    if not path.exists():
        sys.exit("Grid file not found — run scripts/download_grid.py first")
    with tempfile.TemporaryDirectory() as folder:
        unpacked = Path(folder) / NC.name
        with gzip.open(path, "rb") as source, unpacked.open("wb") as target:
            shutil.copyfileobj(source, target)
        grid = xr.open_dataset(unpacked, mask_and_scale=False)
        try:
            yield grid
        finally:
            grid.close()


def copy_anomalies(cur, grid: xr.Dataset, start_year: int) -> int:
    lat_n, lon_n = grid.sizes["lat"], grid.sizes["lon"]
    cell_ids = np.arange(1, lat_n * lon_n + 1, dtype=np.int32)       # row-major: lat, then lon
    times = pd.to_datetime(grid["time"].values)
    keep = np.flatnonzero(times.year >= start_year)
    total = 0
    with cur.copy("COPY grid_anomalies (obs_date, cell_id, anomaly_c) FROM STDIN (FORMAT csv)") as copy:
        for first in range(0, len(keep), CHUNK_MONTHS):
            idx = keep[first:first + CHUNK_MONTHS]
            values = grid["tempanomaly"].isel(time=idx).values.reshape(len(idx), -1)   # (months, cells)
            month, cell = np.nonzero(values != FILL)
            frame = pd.DataFrame({
                "obs_date": times[idx].to_period("M").to_timestamp().strftime("%Y-%m-%d").values[month],
                "cell_id": cell_ids[cell],
                "anomaly_c": values[month, cell],
            })
            buffer = io.StringIO()
            frame.to_csv(buffer, header=False, index=False)
            copy.write(buffer.getvalue())
            total += len(frame)
            print(f"       {times[idx[-1]].year}: {total:>12,} rows", end="\r", flush=True)
    print()
    return total


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--start-year", type=int, default=1880)
    args = parser.parse_args()

    manifest = json.loads((GRID_DIR / "manifest.json").read_text(encoding="utf-8"))
    with open_grid() as grid:
        return load(grid, args, manifest)


def load(grid: xr.Dataset, args: argparse.Namespace, manifest: dict) -> int:
    lat, lon = grid["lat"].values, grid["lon"].values
    # The cells are generated in SQL below; make sure they match the file's coordinates.
    if not (np.allclose(lat, -89 + 2 * np.arange(90)) and np.allclose(lon, -179 + 2 * np.arange(180))):
        sys.exit("Unexpected grid coordinates in the NetCDF file")

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("SET search_path = public, postgis")
        cur.execute("SET LOCAL synchronous_commit = off")

        t = step("clearing previous grid data")
        cur.execute("ALTER TABLE grid_anomalies DROP CONSTRAINT IF EXISTS grid_anomalies_pkey")
        cur.execute("ALTER TABLE grid_anomalies DROP CONSTRAINT IF EXISTS grid_anomalies_cell_fkey")
        cur.execute("DROP INDEX IF EXISTS grid_anomalies_date_brin")
        cur.execute("TRUNCATE cell_countries, grid_anomalies, grid_cells, countries RESTART IDENTITY")
        cur.execute("DELETE FROM datasets WHERE name = %s", (DATASET_NAME,))
        done(t, "cleared")

        t = step("grid_cells")
        cur.execute(
            """
            INSERT INTO grid_cells (cell_id, lat, lon, area_weight, geom)
            SELECT i * 180 + j + 1,
                   -89 + 2 * i,
                   -179 + 2 * j,
                   -- exact share of a sphere between two latitudes and over 2° of longitude
                   (sin(radians(-88 + 2 * i)) - sin(radians(-90 + 2 * i))) * radians(2) / (4 * pi()),
                   ST_MakeEnvelope(-180 + 2 * j, -90 + 2 * i, -178 + 2 * j, -88 + 2 * i, 4326)
            FROM   generate_series(0, 89) AS i, generate_series(0, 179) AS j
            """
        )
        cur.execute("SELECT count(*), round(sum(area_weight)::numeric, 9) FROM grid_cells")
        cells, weight = cur.fetchone()
        done(t, f"{cells:,} cells, total area weight {weight}")

        t = step(f"grid_anomalies from {args.start_year} (COPY)")
        rows = copy_anomalies(cur, grid, args.start_year)
        done(t, f"{rows:,} rows")

        t = step("primary key, foreign key and BRIN index")
        cur.execute("ALTER TABLE grid_anomalies ADD CONSTRAINT grid_anomalies_pkey PRIMARY KEY (cell_id, obs_date)")
        cur.execute("ALTER TABLE grid_anomalies ADD CONSTRAINT grid_anomalies_cell_fkey "
                    "FOREIGN KEY (cell_id) REFERENCES grid_cells (cell_id)")
        cur.execute("CREATE INDEX grid_anomalies_date_brin ON grid_anomalies USING brin (obs_date)")
        done(t, "constraints built")

        t = step("countries")
        features = json.loads(COUNTRIES.read_text(encoding="utf-8"))["features"]
        cur.executemany(
            """
            INSERT INTO countries (adm0_a3, iso_a3, name, continent, geom)
            VALUES (%s, NULLIF(%s, '-99'), %s, %s,
                    ST_Multi(ST_CollectionExtract(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)), 3)))
            """,
            [(f["properties"]["ADM0_A3"], f["properties"]["ISO_A3"], f["properties"]["NAME"],
              f["properties"]["CONTINENT"], json.dumps(f["geometry"])) for f in features],
        )
        done(t, f"{len(features)} countries")

        t = step("cell_countries (spatial join)")
        cur.execute(
            """
            INSERT INTO cell_countries (cell_id, country_id, overlap_km2)
            SELECT cell_id, country_id, overlap_km2
            FROM  (SELECT g.cell_id,
                          c.country_id,
                          ST_Area(ST_Intersection(g.geom, c.geom)::geography) / 1e6 AS overlap_km2
                   FROM   grid_cells g
                   JOIN   countries  c ON ST_Intersects(g.geom, c.geom)) x
            WHERE  overlap_km2 > 0
            """
        )
        done(t, f"{cur.rowcount:,} cell-country pairs")

        t = step("dataset record, statistics and materialized views")
        cur.execute(
            """
            INSERT INTO datasets (name, source_url, base_period_start, base_period_end, downloaded_at)
            VALUES (%s, %s, 1951, 1980, %s)
            """,
            (DATASET_NAME, manifest["files"][NC_GZ.name]["url"], manifest["downloaded_at"]),
        )
        cur.execute("ANALYZE grid_cells, grid_anomalies, countries, cell_countries")
        for view in ("mv_grid_annual", "mv_grid_trends", "mv_country_annual"):
            cur.execute(f"REFRESH MATERIALIZED VIEW {view}")
        cur.execute("ANALYZE mv_grid_annual, mv_grid_trends, mv_country_annual")
        done(t, "refreshed")

        # Validation: the area-weighted mean of all cells must track NASA's official global series.
        cur.execute(
            """
            WITH grid AS (
                SELECT a.year, SUM(a.anomaly * c.area_weight) / SUM(c.area_weight) AS anomaly
                FROM   mv_grid_annual a JOIN grid_cells c USING (cell_id)
                GROUP  BY a.year
            ),
            official AS (
                SELECT year, AVG(anomaly) AS anomaly
                FROM   v_monthly WHERE region = 'GLB'
                GROUP  BY year HAVING COUNT(anomaly) = 12
            )
            SELECT COUNT(*), AVG(ABS(g.anomaly - o.anomaly)), MAX(ABS(g.anomaly - o.anomaly)),
                   corr(g.anomaly, o.anomaly)
            FROM   grid g JOIN official o USING (year)
            WHERE  g.year >= GREATEST(1950, %s)
            """,
            (args.start_year,),
        )
        years, mean_diff, max_diff, correlation = cur.fetchone()
        print(f"CHECK  grid vs official global mean ({years} years): "
              f"mean |diff| {float(mean_diff):.3f} °C, max {float(max_diff):.3f} °C, r = {float(correlation or 0):.4f}")
        if float(mean_diff) > 0.05:
            raise RuntimeError("Grid global mean does not match NASA's global series — load aborted")

    print("Grid loaded.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
