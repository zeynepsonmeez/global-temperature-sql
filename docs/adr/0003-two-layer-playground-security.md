# 0003 — Two independent security layers for the SQL Playground

**Status:** Accepted

## Context

The SQL Playground runs SQL typed by anyone who opens the app. Checking that a query "starts
with SELECT" is easy to bypass (`SELECT 1; DROP …`, a data-modifying CTE, `SELECT … INTO`,
`pg_sleep`).

## Decision

1. **Application layer — `app/sql_guard.py`:** parse the query with sqlglot; accept exactly one
   statement whose syntax tree contains no write, DDL, `INTO`, transaction or blocked function.
   Its job is to explain problems in plain language.
2. **Database layer — `database/roles.sql`:** the app connects as `gts_reader`, which can only
   read the views in a dedicated `playground` schema (and use PostGIS functions), has no
   `CREATE` or `TEMPORARY` privilege anywhere, a 3-second statement timeout and memory limits.
   This layer is the real boundary.

Row limits are applied with `fetchmany`, never by rewriting the user's SQL.

## Consequences

- `tests/test_reader_role.py` attacks the role directly, without the validator. It showed that
  `default_transaction_read_only` alone is not a boundary — a client can open
  `BEGIN READ WRITE` — while missing privileges still stop every write.
- New tables are invisible to the Playground until a view is added to `roles.sql`.

## Alternatives considered

- **Validator only:** one parsing bug would expose the database.
- **Database permissions only:** safe, but users would get raw PostgreSQL errors instead of
  explanations.
