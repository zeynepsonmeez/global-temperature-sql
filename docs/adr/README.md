# Architecture Decision Records

Short records of the decisions that shaped this project: the context, what was decided, the
consequences and the alternatives that were considered. Format adapted from Michael Nygard's
"Documenting Architecture Decisions" (2011).

| # | Decision | Status |
|---|---|---|
| [0001](0001-postgresql-in-docker.md) | Run PostgreSQL (with PostGIS) in Docker | Accepted |
| [0002](0002-normalised-schema-and-recomputed-aggregates.md) | Normalised schema with natural keys; recompute NASA's aggregates in SQL | Accepted |
| [0003](0003-two-layer-playground-security.md) | Two independent security layers for the SQL Playground | Accepted |
| [0004](0004-grid-storage.md) | Store the 25M-row grid as SMALLINT hundredths, partitioned by decade | Accepted |
| [0005](0005-indexing-strategy.md) | Primary key + BRIN + materialized views, chosen by measurement | Accepted |
| [0006](0006-postgis-in-its-own-schema.md) | Install PostGIS in its own schema | Accepted |
| [0007](0007-regression-design.md) | Trend + ENSO regression from 1970 with Newey-West errors | Accepted |
| [0008](0008-streamlit-without-sidebar.md) | Streamlit UI without a sidebar, light theme by default | Accepted |
| [0009](0009-streamlit-customisations.md) | Streamlit customisations outside its public API, kept in one place and pinned | Accepted |
