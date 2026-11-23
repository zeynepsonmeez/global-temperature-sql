"""Load the processed CSVs into PostgreSQL as one dataset snapshot.

Usage:
    python scripts/load_data.py

Requires the database schema (database/schema.sql) and the output of clean_data.py.
Idempotent: loading the same snapshot twice replaces it instead of duplicating rows.
Everything runs in a single transaction — on any error nothing is written.
"""

from __future__ import annotations

import json
import sys
from email.utils import parsedate_to_datetime

import pandas as pd

from clean_data import PROCESSED_DIR, RAW_DIR
from db import get_connection

DATASET_NAME = "GISTEMP v4"
BASE_PERIOD = (1951, 1980)


def read_processed(name: str) -> pd.DataFrame:
    path = PROCESSED_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"{path} not found — run scripts/clean_data.py first")
    return pd.read_csv(path)


def as_rows(frame: pd.DataFrame) -> list[tuple]:
    """DataFrame -> list of tuples, with NaN turned into None (SQL NULL)."""
    clean = frame.astype(object).where(frame.notna(), None)
    return list(clean.itertuples(index=False, name=None))


def main() -> int:
    manifest = json.loads((RAW_DIR / "manifest.json").read_text(encoding="utf-8"))
    last_modified = manifest["files"]["GLB.Ts+dSST.csv"]["last_modified"]

    regions = read_processed("regions.csv")
    monthly = read_processed("monthly_anomalies.csv")
    zonal = read_processed("zonal_annual_anomalies.csv")

    # The connection block commits on success and rolls back on any exception;
    # kept separate from the cursor block so that boundary stays visible.
    with get_connection() as conn:  # noqa: SIM117
        with conn.cursor() as cur:
            # 1. Regions: insert new ones, update names/bounds of existing ones.
            cur.executemany(
                """
                INSERT INTO regions (code, name, kind, lat_min, lat_max)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (code) DO UPDATE
                SET name = EXCLUDED.name, kind = EXCLUDED.kind,
                    lat_min = EXCLUDED.lat_min, lat_max = EXCLUDED.lat_max
                """,
                as_rows(regions[["code", "name", "kind", "lat_min", "lat_max"]]),
            )
            cur.execute("SELECT code, region_id FROM regions")
            region_ids = dict(cur.fetchall())

            # 2. Dataset snapshot: re-loading the same download replaces it (ON DELETE CASCADE
            #    removes its anomaly rows), so the script can be run any number of times.
            cur.execute(
                "DELETE FROM datasets WHERE name = %s AND downloaded_at = %s",
                (DATASET_NAME, manifest["downloaded_at"]),
            )
            cur.execute(
                """
                INSERT INTO datasets (name, source_url, base_period_start, base_period_end,
                                      downloaded_at, source_last_modified)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING dataset_id
                """,
                (DATASET_NAME, manifest["source_url"], *BASE_PERIOD,
                 manifest["downloaded_at"],
                 parsedate_to_datetime(last_modified) if last_modified else None),
            )
            dataset_id = cur.fetchone()[0]

            # 3. Anomalies via COPY — PostgreSQL's bulk-load path, much faster than INSERTs.
            monthly.insert(0, "dataset_id", dataset_id)
            monthly["region_code"] = monthly["region_code"].map(region_ids)
            with cur.copy(
                "COPY monthly_anomalies (dataset_id, region_id, year, month, anomaly) FROM STDIN"
            ) as copy:
                for row in as_rows(monthly):
                    copy.write_row(row)

            zonal.insert(0, "dataset_id", dataset_id)
            zonal["region_code"] = zonal["region_code"].map(region_ids)
            with cur.copy(
                "COPY zonal_annual_anomalies (dataset_id, region_id, year, anomaly) FROM STDIN"
            ) as copy:
                for row in as_rows(zonal):
                    copy.write_row(row)

            # 4. Verify before committing: the database must hold exactly what we sent.
            for table, expected in (("monthly_anomalies", len(monthly)),
                                    ("zonal_annual_anomalies", len(zonal))):
                cur.execute(f"SELECT count(*) FROM {table} WHERE dataset_id = %s", (dataset_id,))
                actual = cur.fetchone()[0]
                if actual != expected:
                    raise RuntimeError(f"{table}: expected {expected} rows, found {actual}")

            # 5. Planner statistics now, not whenever autovacuum gets to it: the Playground's
            #    cost gate asks the planner, which otherwise sees freshly loaded tables as tiny.
            cur.execute("ANALYZE regions, datasets, monthly_anomalies, zonal_annual_anomalies")

    print(f"OK     dataset_id={dataset_id}  ({DATASET_NAME}, downloaded {manifest['downloaded_at']})")
    print(f"OK     regions                 {len(regions):>5} rows")
    print(f"OK     monthly_anomalies       {len(monthly):>5} rows")
    print(f"OK     zonal_annual_anomalies  {len(zonal):>5} rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
