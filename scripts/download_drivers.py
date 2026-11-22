"""Download the climate-driver series into data/raw/drivers/ (small files, committed).

Usage:
    python scripts/download_drivers.py

  * oni.ascii.txt   — NOAA CPC Oceanic Niño Index (ENSO), 3-month running means since 1950
  * co2_mm_mlo.csv  — NOAA GML Mauna Loa monthly mean CO2 since March 1958
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone

from db import ROOT
from download_data import download

DRIVERS_DIR = ROOT / "data" / "raw" / "drivers"

SOURCES = {
    "oni.ascii.txt": (
        "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt",
        "NOAA CPC Oceanic Nino Index: 3-month running mean SST anomaly in the Nino 3.4 region",
    ),
    "co2_mm_mlo.csv": (
        "https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_mm_mlo.csv",
        "NOAA GML Mauna Loa monthly mean atmospheric CO2 (ppm)",
    ),
}


def main() -> int:
    DRIVERS_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {"downloaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "files": {}}
    for name, (url, description) in SOURCES.items():
        try:
            content, last_modified = download(url)
        except OSError as error:
            print(f"ERROR  {name}: {error}", file=sys.stderr)
            return 1
        if content.lstrip()[:1] == b"<":
            print(f"ERROR  {name}: server returned HTML instead of data", file=sys.stderr)
            return 1
        (DRIVERS_DIR / name).write_bytes(content)
        manifest["files"][name] = {
            "description": description, "url": url, "bytes": len(content),
            "last_modified": last_modified, "sha256": hashlib.sha256(content).hexdigest(),
        }
        print(f"OK     {name:<16} {len(content):>8,} bytes")
    (DRIVERS_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("Manifest written to data/raw/drivers/manifest.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
