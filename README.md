# GlobalTemperatureSQL

**Query the Data. Understand the Climate.**

An interactive SQL-powered platform for exploring and analyzing historical global temperature anomalies using NASA GISTEMP v4 data.

> 🚧 Work in progress — data pipeline (download → clean → validate) is done; PostgreSQL schema is next.

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

python scripts/download_data.py # fetch the latest NASA tables into data/raw/
python scripts/clean_data.py    # validate and convert to long format in data/processed/
pytest                          # run the data tests
```

## Project structure

```text
data/raw/         NASA files as downloaded + manifest.json (snapshot metadata)
data/processed/   cleaned long-format CSVs (generated, not committed)
docs/DATA.md      data dictionary, validation checks and known limitations
scripts/          download and cleaning scripts
tests/            data tests (pytest)
```

## Data source

NASA GISS Surface Temperature Analysis (GISTEMP v4) — https://data.giss.nasa.gov/gistemp/
Anomalies are in °C relative to the 1951–1980 mean. See [docs/DATA.md](docs/DATA.md).
