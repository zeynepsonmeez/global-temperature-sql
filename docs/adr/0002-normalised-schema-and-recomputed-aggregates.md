# 0002 — Normalised schema with natural keys; recompute NASA's aggregates in SQL

**Status:** Accepted

## Context

NASA publishes one row per year with twelve month columns plus derived columns (annual `J-D`,
seasonal `DJF`, …). Every download is a new snapshot, and NASA revises past values slightly.

## Decision

- **Long format:** one row per region, year and month (`monthly_anomalies`).
- **Separate tables** for monthly series (GLB/NH/SH) and annual latitude bands, instead of one
  table with a nullable `month` that could not be part of the primary key.
- **Natural primary keys** — `(dataset_id, region_id, year, month)` — which also reject a month
  loaded twice; no surrogate `id` column.
- **`datasets` table** for snapshots, so revisions can be compared and every result traced to
  its source file (manifest with SHA-256).
- **`NUMERIC(4,2)`** for anomalies: NASA publishes two decimals; floating point would not
  represent them exactly. Missing values (`***`) are `NULL`, never 0.
- **Derived columns are not stored.** Annual and seasonal means are recomputed in SQL and
  tested against NASA's columns (largest difference 0.0067 °C, from rounding).

## Consequences

- Queries filter with `WHERE month = 7` instead of choosing among twelve columns.
- A test (`test_sql_annual_mean_matches_nasa_j_d`) proves the SQL aggregation reproduces NASA.
- The `v_latest_dataset` view must filter by dataset name, because other snapshots (the grid)
  are recorded in the same table — a bug caught by the tests when the grid was added.

## Alternatives considered

- **Keep NASA's wide layout:** fewer rows, but awkward SQL and no natural key per month.
- **Store NASA's annual columns:** convenient, but duplicates information and hides errors that
  recomputing them reveals.
