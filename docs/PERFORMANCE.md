# Performance study: indexing a 25-million-row climate grid

How should `grid_anomalies` — 25,448,605 monthly values on a 2°×2° grid — be stored and
indexed? This study measures five strategies on four real queries from the app.

Reproduce with `python scripts/benchmark.py`; raw numbers are in
[`benchmark_results.json`](benchmark_results.json). Machine: a laptop running PostgreSQL 17.11
in Docker (`shared_buffers = 512MB`, `work_mem = 32MB`). Each query ran once to warm the
cache and then 5 times; the table shows the **median execution time** from
`EXPLAIN (ANALYZE, BUFFERS)`. Absolute times depend on the machine; the ratios are the result.

## The queries

| | Query | Filter | Who needs it |
|---|---|---|---|
| **Q1** | Every cell for one month | `obs_date = '2024-07-01'` | a map |
| **Q2** | Area-weighted global mean per year, 2020–2024 | 5-year date range + join | a trend line |
| **Q3** | Full history of one cell (Ankara) | `cell_id = 11627` | a local time series |
| **Q4** | Türkiye's monthly series from the raw grid | spatial join via `cell_countries` | a country page |

## Results (median, milliseconds)

| Strategy | Q1 month | Q2 5 years | Q3 one cell | Q4 country | Index size | Build |
|---|---:|---:|---:|---:|---:|---:|
| Flat table, no index | 349.8 | 465.7 | 348.4 | 1,068.8 | — | — |
| + B-tree `(obs_date)` | **2.2** | 212.5 | 425.2 | 1,045.8 | 169 MB | 4.1 s |
| + BRIN `(obs_date)` | 2.9 | 222.6 | 437.0 | 1,134.8 | **0.04 MB** | 1.2 s |
| + B-tree `(cell_id, obs_date)` | 322.1 | 536.7 | **0.8** | **37.4** | 545 MB | 9.5 s |
| **Partitioned by decade + PK `(cell_id, obs_date)` + BRIN** *(production)* | **2.4** | **212.3** | **1.4** | **41.6** | 545 MB | — |
| Materialized view `v_country_annual` (Q4, annual) | | | | **0.1** | | |

The flat table itself is 880 MB.

## What the numbers say

**1. An index only helps queries that filter on its leading column.**
The B-tree on `(obs_date)` makes Q1 **160× faster** (350 → 2.2 ms) but does nothing for Q3,
which filters on `cell_id`. The B-tree on `(cell_id, obs_date)` is the mirror image: Q3 drops
from 348 to **0.8 ms (~430×)** while Q1 stays at a full scan (322 ms), because the index is
sorted by cell first and a single date is scattered across all of it. Column order in a
composite index is a design decision, not a detail.

**2. BRIN gives B-tree speed for 1/4,000 of the space — when the data is physically ordered.**
The table is loaded month by month, so rows sit on disk in date order. A BRIN index stores only
the min/max date of each block range: **40 KB instead of 169 MB**, built in 1.2 s instead of
4.1 s, and Q1 takes 2.9 ms instead of 2.2 ms. BRIN would be useless on randomly ordered data;
here it is almost free.

**3. Range aggregates are bound by the amount of data, not by finding it.**
Q2 reads five years ≈ 870,000 rows and joins them. Any date index halves the time
(466 → ~212 ms) by skipping the other 140 years, but the remaining cost is aggregating the
rows themselves. No index can remove that; pre-aggregation can (point 5).

**4. Partitioning wins on the partition key and pays a small price elsewhere.**
With one partition per decade, Q1 and Q2 read only the partitions that can contain the
dates (verified in the plans: Q1 touches 1 of 16 partitions). Q3 filters on `cell_id`, so it
must probe the primary-key index of all 16 partitions: 1.4 ms instead of 0.8 ms on a single
index. Partitioning also makes maintenance cheaper: a decade can be re-loaded, vacuumed or
dropped on its own.

**5. The fastest query is the one already computed.**
Q4 joins 25 M rows with the country overlap table. The composite index brings it from
1,069 ms to ~40 ms; the materialized view `v_country_annual` answers the annual version in
**0.1 ms — about 10,000× faster than the raw scan**. The trade-off is freshness:
materialized views are refreshed by `load_grid.py` after each load.

## The production design

```text
grid_anomalies  PARTITION BY RANGE (obs_date) — one partition per decade
  ├─ PRIMARY KEY (cell_id, obs_date)   → fast per-cell lookups (Q3, Q4), enforces uniqueness
  └─ BRIN (obs_date)                   → cheap date filtering inside a partition
materialized views (annual per cell, per country, trends) → app pages answer in < 1 ms
```

It is the only strategy in the table that is fast on **all four** query shapes — the
"best-of-both" of points 1, 2 and 4, plus point 5 for the pages users open most.

## Other storage decisions

- **`anomaly_c SMALLINT` (hundredths of a degree)** instead of `REAL` or `NUMERIC`:
  NASA ships the grid as `int16 × 0.01`, so this is lossless (verified cell by cell in
  `tests/test_grid.py`) and takes 2 bytes. Column order `(date, smallint, smallint)` packs each
  row's data into 8 bytes with no alignment padding.
- **Missing cells are not stored**: 3.1 M of the 28.5 M grid positions have no data (mostly
  polar and early ocean cells). Storing NULLs would add 12% rows for nothing.
- **Constraints after the bulk load**: `COPY` into an unindexed table took 22 s; building the
  primary key, foreign key and BRIN index afterwards took 10 s in total — far faster than
  maintaining them for 25 M individual inserts.
- **Server settings** (`docker-compose.yml`): `shm_size: 512mb` (Docker's 64 MB default breaks
  parallel queries on this table), larger `shared_buffers` and `maintenance_work_mem` for index
  builds, `random_page_cost = 1.1` for SSD storage.
