# GlobalTemperatureSQL

**Query the Data. Understand the Climate.**

An interactive SQL-powered platform for exploring and analyzing historical global temperature anomalies using NASA GISTEMP v4 data.

> 🚧 Work in progress — data pipeline and PostgreSQL database are done; SQL analyses are next.

## Quick start

Requirements: Python 3.11+, Docker.

```bash
# 1. Python environment
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

# 2. Database (PostgreSQL 17 in Docker, on localhost:5433)
cp .env.example .env            # then set your own POSTGRES_PASSWORD
docker compose up -d
docker compose exec -T db sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < database/schema.sql

# 3. Data pipeline
python scripts/download_data.py # fetch the latest NASA tables into data/raw/
python scripts/clean_data.py    # validate and convert to long format in data/processed/
python scripts/load_data.py     # load into PostgreSQL as one dataset snapshot

# 4. Tests (database tests are skipped if the database is not running)
pytest
```

## Database

| Object | Description |
|---|---|
| `datasets` | One row per downloaded NASA snapshot (data versioning) |
| `regions` | Global, hemispheres and 11 latitude bands with their bounds |
| `monthly_anomalies` | GLB / NH / SH, one row per month; primary key `(dataset_id, region_id, year, month)` |
| `zonal_annual_anomalies` | Latitude bands, one row per year |
| `v_monthly`, `v_annual` | Latest snapshot with region codes — the easiest place to start querying |

## Project structure

```text
data/raw/         NASA files as downloaded + manifest.json (snapshot metadata)
data/processed/   cleaned long-format CSVs (generated, not committed)
database/         schema.sql
docs/DATA.md      data dictionary, validation checks and known limitations
scripts/          download, cleaning and loading scripts
tests/            data and database tests (pytest)
```

## Data source

NASA GISS Surface Temperature Analysis (GISTEMP v4) — https://data.giss.nasa.gov/gistemp/
Anomalies are in °C relative to the 1951–1980 mean. See [docs/DATA.md](docs/DATA.md).
