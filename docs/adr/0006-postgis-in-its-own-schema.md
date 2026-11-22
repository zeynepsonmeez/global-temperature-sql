# 0006 — Install PostGIS in its own schema

**Status:** Accepted

## Context

The read-only role must call PostGIS functions in the Playground (`ST_Contains`, `ST_Area`, …)
but must not see the tables in the `public` schema. If PostGIS lives in `public`, using its
functions requires `USAGE` on `public`.

## Decision

Create the extension in a dedicated `postgis` schema and grant the reader `USAGE` on that
schema only; the database and role search paths include it.

The `postgis/postgis` Docker image pre-installs PostGIS (plus topology and the tiger geocoder)
into `public` when it creates a new database, and PostGIS cannot be moved with
`ALTER EXTENSION … SET SCHEMA`. `database/spatial_schema.sql` therefore detects that case,
drops the extension and re-creates it in `postgis`, and removes the empty schemas left behind.

## Consequences

- The Playground can teach spatial SQL without widening the reader's privileges.
- This only appeared on a **fresh** database: the first one had been created by the plain
  `postgres` image. Rebuilding from scratch and running the tests caught it — CI would have
  failed in the same way.

## Alternatives considered

- **Grant `USAGE` on `public`:** simplest, but weakens the security model of ADR 0003.
- **Wrap every needed PostGIS function in the playground schema:** brittle and incomplete.
