# 0005 — Primary key + BRIN + materialized views, chosen by measurement

**Status:** Accepted

## Context

The grid is queried in three shapes: by date (a map of one month), by cell (one location's
history) and by country (a spatial join). No single index serves all three.

## Decision

Measure before choosing (`scripts/benchmark.py`, results in `docs/PERFORMANCE.md`), then use:

- decade partitions (date queries are pruned to one partition);
- primary key `(cell_id, obs_date)` (cell and country queries);
- a BRIN index on `obs_date` (date filtering inside a partition, ~40 KB);
- materialized views for the pages users open most (annual per cell, per country, trends).

## Consequences

| Query | No index | Production design |
|---|---:|---:|
| One month, all cells | 350 ms | 2.4 ms |
| One cell, all months | 348 ms | 1.4 ms |
| One country | 1,069 ms | 42 ms; 0.1 ms from the materialized view |

Materialized views must be refreshed after each load (`load_grid.py` does it in the same
transaction).

## Alternatives considered

- **B-tree on `obs_date` only:** fast maps, useless for cell queries.
- **B-tree on `(cell_id, obs_date)` only:** fast cell queries, a full scan for maps.
- **B-tree instead of BRIN on the date:** similar speed, 4,000× larger.
