# 0004 — Store the 25M-row grid as SMALLINT hundredths, partitioned by decade

**Status:** Accepted

## Context

NASA's 2°×2° grid holds 25,448,605 monthly values (16,200 cells × 1,762 months, minus
missing cells). NASA stores them as `int16` hundredths of a degree with `32767` as missing.
Disk space on the development machine is limited.

## Decision

- **`anomaly_c SMALLINT`** (hundredths of a degree): lossless and 2 bytes; the view `v_grid`
  converts to °C. Columns ordered `(obs_date, cell_id, anomaly_c)` so each row's data packs
  into 8 bytes without alignment padding.
- **Missing cells are not stored** (no NULL rows): 3.1 M fewer rows.
- **Range partitions by decade** on `obs_date`.
- **Bulk load with COPY into an unindexed table**, then build the primary key, foreign key and
  BRIN index once (22 s + 10 s for the full grid).
- The NetCDF file is unpacked to a temporary folder and deleted after loading.

## Consequences

- The grid takes about 1.4 GB including its primary key.
- A test compares every cell of one month with the NetCDF file to prove storage is lossless.
- Queries on a date range read only the partitions they need (verified in the plans).

## Alternatives considered

- **`REAL` or `NUMERIC`:** 4–8 bytes per value with no gain in precision.
- **One wide row per cell (array of months):** compact, but loses relational querying by date.
- **No partitioning:** simpler, but every date query scans the whole table without an index.
