# SQL Playground security

The Playground runs SQL typed by anyone who opens the app. It is protected by two
independent layers, so a mistake in one is caught by the other.

## Layer 1 — query validation in the app (`app/sql_guard.py`)

Checking that a query "starts with SELECT" is not enough, so every query is parsed into a
syntax tree with [sqlglot](https://github.com/tobymao/sqlglot) and rejected when:

| Rule | Example it stops |
|---|---|
| More than one statement | `SELECT 1; DROP TABLE regions` |
| The root is not a query | `DELETE FROM ...`, `SET ...`, `COPY ...`, `BEGIN` |
| A write or DDL node appears anywhere in the tree | `WITH d AS (DELETE ... RETURNING *) SELECT ...` |
| `SELECT ... INTO` | `SELECT * INTO copy FROM regions` (creates a table) |
| A blocked function is called | `pg_sleep`, `pg_read_file`, `set_config`, `dblink`, ... |
| The text is longer than 5,000 characters | very large generated queries |

The validator also turns the reason into a plain-language message.

## Layer 2 — the database role (`database/roles.sql`) — the real boundary

The app connects as `gts_reader`, never as the owner:

- **Privileges:** `USAGE` on the `playground` schema and `SELECT` on its views only, plus
  `USAGE` on the `postgis` schema so spatial functions work. PostGIS is installed in its own
  schema precisely so that this grant does not open the `public` schema. No access to base
  tables, no `CREATE` anywhere, no `TEMPORARY`.
- **Session limits:** `statement_timeout = 3s`, `idle_in_transaction_session_timeout = 10s`,
  `work_mem = 8MB`, `temp_file_limit = 32MB`, `CONNECTION LIMIT 20`.
- **Read-only transactions:** the role defaults to read-only and the app opens every
  transaction as `READ ONLY`.
- **Row limit:** results are read through a **server-side cursor** with `fetchmany(1000 + 1)`, so
  PostgreSQL sends only those rows; the user's SQL is never rewritten. (A client-side cursor
  would first transfer the entire result — all 25 million rows of `SELECT * FROM v_grid`.)

## Between the layers — the EXPLAIN cost gate (`app/database.py`)

After the validator accepts a query and before it runs, the app asks the planner for its cost
with `EXPLAIN (FORMAT JSON)`, which plans the query **without executing it**. Queries whose
estimated cost exceeds `MAX_PLAN_COST` (2,000,000) are refused with an explanation of what is
expensive and how to fix it.

The limit was calibrated by measuring every query in `sql/` (the most expensive costs about
0.3 M) against deliberately expensive ones: a triple self-join of `v_monthly` costs ~2 billion,
an unconditioned join of the grid with itself ~8.6 trillion. The timeout would stop those
queries after 3 seconds anyway; the gate stops them before they use any CPU, and tells the
visitor why.

Calibrating the gate also surfaced two real problems, both fixed:
an index was missing on `cell_countries (cell_id)` (query S6 cost 3.4 M, now under 0.1 M), and
query S9 exceeded the reader's temporary-file limit and failed in the Playground (rewritten to
avoid a large sort). `tests/test_errors.py` now runs every library query as the read-only role
through the gate, exactly as a visitor would.
- **Network:** the database port is bound to `127.0.0.1` only (`docker-compose.yml`).

### Lesson learned while testing

`default_transaction_read_only` is **not** a security boundary by itself: a client can start
`BEGIN READ WRITE` and override it. `tests/test_reader_role.py` simulates exactly that and shows
that writes are still refused — by missing privileges, not by the read-only flag.

## Tests

| File | What it proves |
|---|---|
| `tests/test_sql_guard.py` | 24 attack queries are blocked; all 37 library queries are allowed |
| `tests/test_reader_role.py` | Without the validator, the database still blocks writes, base tables, file access, server programs and long queries |
| `tests/test_app.py` | The Playground blocks a `DROP` and explains a permission error |

## Reporting

This is a portfolio project. If you find a way around these protections, please open an issue.
