"""Clean NASA GISTEMP v4 tables and convert them from wide to long format.

Usage:
    python scripts/clean_data.py

Reads  data/raw/*.csv        (as downloaded by download_data.py)
Writes data/processed/regions.csv
       data/processed/monthly_anomalies.csv         (GLB, NH, SH — one row per month)
       data/processed/zonal_annual_anomalies.csv    (latitude bands — one row per year)

NASA's own seasonal and annual columns (J-D, D-N, DJF, ...) are NOT written out:
they are derived values that we recompute in SQL and only use here for validation.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"

MISSING_MARKER = "***"  # NASA's placeholder for "no value" — must become NULL, never 0
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

MONTHLY_FILES = {
    "GLB": "GLB.Ts+dSST.csv",
    "NH": "NH.Ts+dSST.csv",
    "SH": "SH.Ts+dSST.csv",
}
ZONAL_FILE = "ZonAnn.Ts+dSST.csv"

# code, name, kind, lat_min, lat_max — codes are NASA's own column labels for traceability.
REGIONS = [
    ("GLB", "Global", "global", -90, 90),
    ("NH", "Northern Hemisphere", "hemisphere", 0, 90),
    ("SH", "Southern Hemisphere", "hemisphere", -90, 0),
    ("24N-90N", "Northern extratropics", "zonal_wide", 24, 90),
    ("24S-24N", "Tropics", "zonal_wide", -24, 24),
    ("90S-24S", "Southern extratropics", "zonal_wide", -90, -24),
    ("64N-90N", "Arctic", "zonal", 64, 90),
    ("44N-64N", "Northern mid-high latitudes", "zonal", 44, 64),
    ("24N-44N", "Northern subtropics", "zonal", 24, 44),
    ("EQU-24N", "Northern tropics", "zonal", 0, 24),
    ("24S-EQU", "Southern tropics", "zonal", -24, 0),
    ("44S-24S", "Southern subtropics", "zonal", -44, -24),
    ("64S-44S", "Southern mid-high latitudes", "zonal", -64, -44),
    ("90S-64S", "Antarctic", "zonal", -90, -64),
]
ZONAL_CODES = [code for code, _, kind, _, _ in REGIONS if kind.startswith("zonal")]

# Plausibility bounds for an anomaly in °C. Real values are far inside these;
# anything outside almost certainly means a parsing error.
ANOMALY_BOUNDS = (-5.0, 5.0)


def regions_frame() -> pd.DataFrame:
    return pd.DataFrame(REGIONS, columns=["code", "name", "kind", "lat_min", "lat_max"])


def read_wide_monthly(path: Path) -> pd.DataFrame:
    """Read a GLB/NH/SH file as NASA publishes it (one row per year, 12 month columns)."""
    # Line 1 is a title ("Land-Ocean: Global Means"), the real header is line 2.
    return pd.read_csv(path, skiprows=1, na_values=MISSING_MARKER)


def to_long_monthly(wide: pd.DataFrame, region_code: str) -> pd.DataFrame:
    """Wide (year x 12 months) -> long (one row per region, year, month)."""
    long = wide.melt(id_vars="Year", value_vars=MONTHS, var_name="month_name", value_name="anomaly")
    long["month"] = long["month_name"].map({name: i for i, name in enumerate(MONTHS, start=1)})
    long = long.rename(columns={"Year": "year"})
    long.insert(0, "region_code", region_code)
    long = long[["region_code", "year", "month", "anomaly"]].sort_values(["year", "month"])

    # Months after the latest published value have not happened yet (e.g. Nov/Dec of the
    # current year). They are not "missing" data, so they are dropped. A *** in the middle
    # of the record would be a real gap and is kept as NULL.
    last_published = long["anomaly"].last_valid_index()
    long = long.loc[:last_published]
    return long.reset_index(drop=True)


def read_zonal_long(path: Path) -> pd.DataFrame:
    """ZonAnn file -> long (one row per latitude band and year)."""
    wide = pd.read_csv(path, na_values=MISSING_MARKER)  # this file has no title line
    long = wide.melt(id_vars="Year", value_vars=ZONAL_CODES, var_name="region_code", value_name="anomaly")
    long = long.rename(columns={"Year": "year"})[["region_code", "year", "anomaly"]]
    return long.sort_values(["region_code", "year"]).reset_index(drop=True)


def validate_monthly(long: pd.DataFrame, wide: pd.DataFrame, region_code: str) -> None:
    """Raise ValueError if the long table is inconsistent with NASA's file."""
    problems = []

    if long.duplicated(["region_code", "year", "month"]).any():
        problems.append("duplicate (region, year, month) rows")
    if not long["month"].between(1, 12).all():
        problems.append("month outside 1..12")
    years = long["year"].drop_duplicates()
    if not years.diff().dropna().eq(1).all():
        problems.append("years are not contiguous")
    low, high = ANOMALY_BOUNDS
    if not long["anomaly"].dropna().between(low, high).all():
        problems.append(f"anomaly outside {ANOMALY_BOUNDS}")

    # Our own annual mean must match NASA's J-D column. NASA averages unrounded values and
    # then rounds, while we average already-rounded values, so allow a 0.01 °C tolerance.
    complete = wide[wide[MONTHS].notna().all(axis=1)]
    diff = (complete[MONTHS].mean(axis=1) - complete["J-D"]).abs()
    if (diff > 0.01).any():
        bad = complete.loc[diff > 0.01, "Year"].tolist()
        problems.append(f"annual mean differs from NASA J-D by > 0.01 in years {bad}")

    # Anomalies are relative to 1951–1980, so that period must average to ~0.
    base = long[long["year"].between(1951, 1980)]["anomaly"].mean()
    if abs(base) > 0.01:
        problems.append(f"1951–1980 mean is {base:+.3f}, expected ~0 (wrong baseline?)")

    if problems:
        raise ValueError(f"{region_code}: " + "; ".join(problems))


def validate_zonal(zonal: pd.DataFrame, zonal_raw: pd.DataFrame, glb_wide: pd.DataFrame) -> None:
    problems = []
    if zonal.duplicated(["region_code", "year"]).any():
        problems.append("duplicate (region, year) rows")
    low, high = ANOMALY_BOUNDS
    if not zonal["anomaly"].dropna().between(low, high).all():
        problems.append(f"anomaly outside {ANOMALY_BOUNDS}")

    # The ZonAnn global column and the GLB file's J-D column are the same series.
    joined = zonal_raw[["Year", "Glob"]].merge(glb_wide[["Year", "J-D"]], on="Year")
    if (joined["Glob"] - joined["J-D"]).abs().max() > 0.005:
        problems.append("ZonAnn 'Glob' does not match GLB 'J-D'")

    if problems:
        raise ValueError("zonal: " + "; ".join(problems))


def main() -> int:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    monthly_parts = []
    wide_by_code = {}
    for code, file_name in MONTHLY_FILES.items():
        wide = read_wide_monthly(RAW_DIR / file_name)
        long = to_long_monthly(wide, code)
        validate_monthly(long, wide, code)
        wide_by_code[code] = wide
        monthly_parts.append(long)
        print(f"OK     {code:<4} {len(long):>5} monthly rows  "
              f"({long['year'].min()}-{long['year'].max()}, NULL: {long['anomaly'].isna().sum()})")
    monthly = pd.concat(monthly_parts, ignore_index=True)

    zonal_raw = pd.read_csv(RAW_DIR / ZONAL_FILE, na_values=MISSING_MARKER)
    zonal = read_zonal_long(RAW_DIR / ZONAL_FILE)
    validate_zonal(zonal, zonal_raw, wide_by_code["GLB"])
    print(f"OK     zonal {len(zonal):>4} annual rows  ({zonal['region_code'].nunique()} bands)")

    regions_frame().to_csv(PROCESSED_DIR / "regions.csv", index=False)
    monthly.to_csv(PROCESSED_DIR / "monthly_anomalies.csv", index=False, float_format="%.2f")
    zonal.to_csv(PROCESSED_DIR / "zonal_annual_anomalies.csv", index=False, float_format="%.2f")
    print(f"Written to {PROCESSED_DIR.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
