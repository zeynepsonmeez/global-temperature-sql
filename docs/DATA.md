# Data dictionary

## Source

NASA GISS Surface Temperature Analysis, version 4 (GISTEMP v4), combined land-surface air and
sea-surface water temperature (`Ts+dSST`). Downloaded by `scripts/download_data.py`; the exact
snapshot (download time, NASA `Last-Modified`, SHA-256) is recorded in `data/raw/manifest.json`.

| Raw file | Content | Layout |
|---|---|---|
| `GLB.Ts+dSST.csv` | Global mean | Title line, then 1 row per year: 12 months + `J-D`, `D-N`, `DJF`, `MAM`, `JJA`, `SON` |
| `NH.Ts+dSST.csv` | Northern Hemisphere mean | Same as GLB |
| `SH.Ts+dSST.csv` | Southern Hemisphere mean | Same as GLB |
| `ZonAnn.Ts+dSST.csv` | Annual means, global + 3 wide + 8 narrow latitude bands | No title line, 1 row per year, complete years only |

## What the values mean

- Values are **temperature anomalies in °C**, not absolute temperatures: the departure from the
  **1951–1980 mean** for the same month and region. Verified: the 1951–1980 monthly values of
  GLB, NH and SH average to −0.0001 °C.
- `J-D` = January–December mean; `D-N` = December (previous year)–November mean;
  `DJF`, `MAM`, `JJA`, `SON` = meteorological seasons (DJF uses the previous December).
- `***` means "no value". It appears where a value cannot be computed yet:
  `D-N` and `DJF` in 1880 (they need December 1879), and the months of the current year
  that NASA has not published. It must be stored as `NULL`, never as `0`.

## Processed files (`scripts/clean_data.py`)

### `regions.csv`

| Column | Type | Description |
|---|---|---|
| `code` | text | NASA's own label (`GLB`, `NH`, `64N-90N`, …) |
| `name` | text | Human-readable name |
| `kind` | text | `global`, `hemisphere`, `zonal_wide` (3 bands) or `zonal` (8 bands) |
| `lat_min`, `lat_max` | integer | Latitude bounds in degrees (south negative) |

### `monthly_anomalies.csv` — GLB, NH, SH

| Column | Type | Description |
|---|---|---|
| `region_code` | text | `GLB`, `NH` or `SH` |
| `year` | integer | 1880 – current year |
| `month` | integer | 1 – 12 |
| `anomaly` | decimal(2) | °C relative to 1951–1980; `NULL` if missing |

Unique key: (`region_code`, `year`, `month`). Months not yet published are omitted.

### `zonal_annual_anomalies.csv` — 11 latitude bands

| Column | Type | Description |
|---|---|---|
| `region_code` | text | One of the `zonal` / `zonal_wide` codes |
| `year` | integer | 1880 – last complete year |
| `anomaly` | decimal(2) | Annual mean anomaly, °C |

Unique key: (`region_code`, `year`).

NASA's seasonal and annual columns are **not** stored: they are recomputed in SQL and used only
to validate our processing.

## Validation checks (run on every `clean_data.py` execution and in `tests/`)

1. No duplicate keys, months within 1–12, contiguous years.
2. Every anomaly within ±5 °C (a parsing-error guard, not a scientific limit).
3. The mean of the 12 monthly values matches NASA's `J-D` within 0.01 °C
   (observed maximum difference: 0.0067 °C, caused by NASA averaging unrounded values).
4. The 1951–1980 mean is ~0, confirming the baseline period.
5. `ZonAnn` `Glob` equals `GLB` `J-D` exactly.

## Known limitations

- Early decades, especially at high latitudes, rely on sparse observations; the Antarctic band
  (`90S-64S`) has very little data before the 1950s and shows large year-to-year variability.
- NASA revises past values slightly when new data arrive; always cite the manifest snapshot.
- Values are rounded to 0.01 °C in the published files.
