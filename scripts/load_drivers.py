"""Parse, validate and load the ENSO (ONI) and CO2 series.

Usage:
    python scripts/load_drivers.py

Requires database/drivers_schema.sql and the files from download_drivers.py.
One transaction; re-running replaces the data.
"""

from __future__ import annotations

import sys

import pandas as pd

from db import get_connection
from download_drivers import DRIVERS_DIR

# Three-letter season label -> centre month of the 3-month window.
SEASON_CENTRE = {"DJF": 1, "JFM": 2, "FMA": 3, "MAM": 4, "AMJ": 5, "MJJ": 6,
                 "JJA": 7, "JAS": 8, "ASO": 9, "SON": 10, "OND": 11, "NDJ": 12}


def read_oni() -> pd.DataFrame:
    raw = pd.read_csv(DRIVERS_DIR / "oni.ascii.txt", sep=r"\s+")
    raw.columns = [c.strip().upper() for c in raw.columns]          # SEAS YR TOTAL ANOM
    if set(raw.SEAS) - set(SEASON_CENTRE):
        raise ValueError(f"unknown ONI season labels: {set(raw.SEAS) - set(SEASON_CENTRE)}")
    # DJF of year Y is centred on January Y (December belongs to Y-1); NDJ of Y on December Y.
    month = raw.SEAS.map(SEASON_CENTRE)
    frame = pd.DataFrame({
        "obs_date": pd.to_datetime(dict(year=raw.YR, month=month, day=1)),
        "season": raw.SEAS,
        "oni": raw.ANOM.round(2),
    })
    return frame


def read_co2() -> pd.DataFrame:
    raw = pd.read_csv(DRIVERS_DIR / "co2_mm_mlo.csv", comment="#")
    frame = pd.DataFrame({
        "obs_date": pd.to_datetime(dict(year=raw.year, month=raw.month, day=1)),
        "co2_ppm": raw.average.round(2),
        "co2_deseason": raw.deseasonalized.round(2),
        # NOAA marks "not available" with negative sentinels (-1, -9.99): store NULL, never the number.
        "days_measured": raw.ndays.where(raw.ndays >= 0).astype("Int64"),
    })
    return frame


def validate(oni: pd.DataFrame, co2: pd.DataFrame) -> None:
    problems = []
    for name, frame in (("oni", oni), ("co2", co2)):
        if frame.obs_date.duplicated().any():
            problems.append(f"{name}: duplicate months")
        expected = pd.date_range(frame.obs_date.min(), frame.obs_date.max(), freq="MS")
        if len(expected) != len(frame):
            problems.append(f"{name}: {len(expected) - len(frame)} missing months")
    if not oni.oni.between(-4, 4).all():
        problems.append("oni outside ±4")
    if not co2.co2_ppm.between(250, 600).all():
        problems.append("co2 outside 250–600 ppm (missing-value sentinel not handled?)")
    # CO2 at Mauna Loa has risen every single year since 1959: annual means must increase.
    annual = co2[co2.obs_date.dt.year.between(1959, co2.obs_date.dt.year.max() - 1)] \
        .groupby(co2.obs_date.dt.year).co2_ppm.mean()
    if not annual.diff().dropna().gt(0).all():
        problems.append("annual CO2 is not strictly increasing")
    if problems:
        raise ValueError("; ".join(problems))


def main() -> int:
    oni, co2 = read_oni(), read_co2()
    validate(oni, co2)
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("TRUNCATE enso_oni, co2_monthly")
        with cur.copy("COPY enso_oni (obs_date, season, oni) FROM STDIN") as copy:
            for row in oni.itertuples(index=False):
                copy.write_row((row.obs_date.date(), row.season, row.oni))
        with cur.copy("COPY co2_monthly (obs_date, co2_ppm, co2_deseason, days_measured) FROM STDIN") as copy:
            for row in co2.itertuples(index=False):
                days = None if pd.isna(row.days_measured) else int(row.days_measured)
                copy.write_row((row.obs_date.date(), row.co2_ppm, row.co2_deseason, days))
        cur.execute("ANALYZE enso_oni, co2_monthly")            # planner statistics (see load_data.py)
    print(f"OK     enso_oni     {len(oni):>5} months  ({oni.obs_date.min():%Y-%m} – {oni.obs_date.max():%Y-%m})")
    print(f"OK     co2_monthly  {len(co2):>5} months  ({co2.obs_date.min():%Y-%m} – {co2.obs_date.max():%Y-%m}), "
          f"days_measured NULL: {co2.days_measured.isna().sum()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
