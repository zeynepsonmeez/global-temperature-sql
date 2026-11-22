# 0001 — Run PostgreSQL (with PostGIS) in Docker

**Status:** Accepted

## Context

The project needs PostgreSQL locally, later with the PostGIS extension, and anyone who clones
the repository should get the same database with as few steps as possible. The development
machine also runs another project's PostgreSQL on the default port 5432.

## Decision

Run the database from `docker-compose.yml` using the `postgis/postgis:17-3.6` image:

- a fixed Compose project name (`global-temperature-sql`), so containers, volumes and networks
  never mix with other Compose projects;
- host port **5433**, bound to `127.0.0.1` only;
- data in a named volume; server settings (shared buffers, WAL size, shared memory) in the
  Compose file, so they are versioned with the code;
- the app itself can run as a second service (`--profile app`).

## Consequences

- One command starts the database; a broken database is rebuilt with `docker compose down -v`
  and the setup scripts, because the whole pipeline is reproducible.
- Connections must use `127.0.0.1`, not `localhost`: on Windows `localhost` first tries IPv6,
  which the container does not listen on, and each connection waited ~5 s for the timeout.
- `max_wal_size` was first set to 4 GB for the bulk load, which kept ~4 GB of WAL on disk
  afterwards; it is now 1 GB.

## Alternatives considered

- **Native installer (EDB):** simpler for one machine, but not reproducible for others and
  harder to reset.
- **SQLite / DuckDB:** no server needed, but the project is meant to practise PostgreSQL
  features (roles, partitioning, PostGIS, materialized views).
