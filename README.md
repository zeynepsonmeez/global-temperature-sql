# GlobalTemperatureSQL

**Query the Data. Understand the Climate.**

An interactive SQL-powered platform for exploring and analyzing historical global temperature
anomalies using NASA GISTEMP v4 data — a PostgreSQL database, a library of 37 SQL analyses,
a Streamlit app with interactive charts, and a secure SQL Playground.

![CI](https://github.com/OWNER/global-temperature-sql/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.13-blue)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-336791)
![License](https://img.shields.io/badge/license-MIT-green)

---

## Features

**Climate Explorer** — seven ready-made analyses with filters (year range, regions, month,
moving average): global trend, hottest years, decades, hemispheres, monthly heatmap,
record tracker and warming by latitude band. Every chart has a **"SQL behind this chart"**
panel and can be opened in the Playground with one click.

**SQL Playground** — write and run read-only SQL against the real database: schema browser,
37 sample queries (basic → advanced), result table with timing, CSV export, quick charts and
five **challenges** whose answers are checked automatically against a reference query.

**Home** — a rotatable globe coloured by the warming of each latitude band, dataset facts and
headline findings computed live from the database. The interface is available in
**English and Turkish**.

## Findings

Computed by the queries in [`sql/`](sql/) on the NASA snapshot of 10 Nov 2026
(anomalies in °C relative to 1951–1980):

| Finding | Query |
|---|---|
| The 10 hottest years all occurred in **2015 or later**; 2024 is the hottest (+1.28 °C). | B2 |
| No month has been cooler than the 1951–1980 average since **September 1992**. | B8 |
| **41 consecutive months** at or above +1.0 °C (June 2023 – October 2026); the previous longest run was 7. | A10 |
| Since 2000 there has not been a single year near the baseline; 5 years were "extreme" (≥ +1.0 °C). | I4 |
| Global warming rate since 1970: **+0.20 °C per decade** (R² = 0.91), about 2.5× the long-term rate. | A6 |
| The **Arctic** (64°N–90°N) has warmed **3× faster** than the globe since 1970. | A7 |
| The hemisphere gap grew from 0.06 °C (1990s) to **0.61 °C** (2020s): the land-rich North warms faster. | I2 |
| Relative to 1880–1900, 2024 reached about +1.50 °C (a single year, not the Paris 20-year average). | I9 |

## Architecture

```text
 NASA GISTEMP CSV ──► download_data.py ──► data/raw/ (+ manifest.json: date, SHA-256)
                                              │
                                    clean_data.py  — wide → long, *** → NULL, 5 validation checks
                                              │
                                     load_data.py  — one transaction, COPY, idempotent
                                              ▼
                     PostgreSQL 17 (Docker) ── public: datasets, regions, monthly_anomalies,
                                              │          zonal_annual_anomalies, views
                                              │ playground: read-only views for the app
                                              ▼
                        Streamlit app  ── connects as gts_reader (read-only role)
                         ├─ Home · Climate Explorer (Plotly)
                         └─ SQL Playground ── sql_guard (sqlglot) ── DB privileges + 3 s timeout
```

## Quick start

Requirements: Python 3.11+, Docker.

```bash
# 1. Python environment
python -m venv .venv
.venv\Scripts\activate                 # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

# 2. Settings: copy and set your own passwords
cp .env.example .env

# 3. Database (PostgreSQL 17 on 127.0.0.1:5433)
docker compose up -d
python scripts/setup_database.py       # schema + read-only role

# 4. Data
python scripts/download_data.py        # optional: refresh from NASA (a snapshot is committed)
python scripts/clean_data.py
python scripts/load_data.py

# 5. Run
streamlit run app/main.py              # http://localhost:8501
pytest                                 # 96 tests
```

## Database

| Object | Description |
|---|---|
| `datasets` | One row per downloaded NASA snapshot (data versioning) |
| `regions` | Global, hemispheres and 11 latitude bands with their bounds |
| `monthly_anomalies` | GLB / NH / SH, one row per month; PK `(dataset_id, region_id, year, month)`, generated `obs_date` |
| `zonal_annual_anomalies` | Latitude bands, one row per year |
| `v_monthly`, `v_annual` | Latest snapshot with region codes — the easiest place to start querying |
| `playground.*` | The only objects the app's read-only role can see |

Design notes: anomalies are `NUMERIC(4,2)` (exact, as published) and nullable (`***` → `NULL`,
never `0`); NASA's own annual/seasonal columns are not stored but recomputed in SQL and
checked against NASA in the tests. Details: [`docs/DATA.md`](docs/DATA.md).

## SQL library

| File | Queries | Topics |
|---|---|---|
| [`sql/basic_queries.sql`](sql/basic_queries.sql) | 10 | SELECT, WHERE, ORDER BY, NULLS LAST, GROUP BY, HAVING, aggregates, LIKE |
| [`sql/intermediate_queries.sql`](sql/intermediate_queries.sql) | 11 | CTEs, self-join, LEFT JOIN, subqueries, EXISTS, UNION ALL, CASE, FILTER, dates |
| [`sql/advanced_queries.sql`](sql/advanced_queries.sql) | 16 | RANK / DENSE_RANK / ROW_NUMBER, LAG / LEAD, moving windows (ROWS vs RANGE), NTILE, PERCENT_RANK, gaps-and-islands, LATERAL, ROLLUP, regr_slope, corr, percentile_cont |

Every query is commented and runs in CI.

## Security

The Playground has two independent layers: a sqlglot-based validator and a PostgreSQL role
that can only read four views, cannot write or create anything, and is stopped after 3 seconds.
See [`docs/SECURITY.md`](docs/SECURITY.md).

## Testing

| Suite | Tests | Covers |
|---|---|---|
| `test_clean_data.py` | 13 | Parsing, `***` → NULL, long format, NASA J-D match, baseline check |
| `test_database.py` | 14 | Row counts, SQL annual mean = NASA J-D, constraints, keys, SQL library runs |
| `test_sql_guard.py` | 34 | 24 attack queries blocked, all library queries allowed |
| `test_reader_role.py` | 10 | Database-level protection without the validator |
| `test_challenges.py` | 15 | Challenge references and the answer checker |
| `test_app.py` | 10 | Every page renders in both languages; Playground runs and blocks queries |

GitHub Actions runs the whole pipeline (schema → clean → load → tests) on every push.

## Project structure

```text
app/                Streamlit app (main.py, views/, sql_guard.py, queries.py, i18n.py, ...)
data/raw/           NASA files as downloaded + manifest.json
data/processed/     cleaned CSVs (generated, not committed)
database/           schema.sql, roles.sql
docs/               DATA.md (data dictionary), SECURITY.md
scripts/            download, clean, load and database setup
sql/                SQL analysis library
tests/              pytest suites
```

## Data source and license

Data: NASA GISS Surface Temperature Analysis (GISTEMP v4), https://data.giss.nasa.gov/gistemp/.
GISTEMP Team, 2026: GISS Surface Temperature Analysis (GISTEMP), version 4. NASA Goddard
Institute for Space Studies. Dataset accessed 2026-11-21.

Code: MIT License © 2026 Zeynep Sönmez. The NASA data is subject to NASA's terms.
