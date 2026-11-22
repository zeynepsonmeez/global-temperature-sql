"""Download the gridded GISTEMP data and the country borders into data/raw/grid/.

Usage:
    python scripts/download_grid.py

Files (too large to commit, so they are re-downloaded and verified by checksum):
  * gistemp1200_GHCNv4_ERSSTv5.nc.gz — NASA GISTEMP v4, 2°x2° grid, 1200 km smoothing
  * ne_50m_admin_0_countries.geojson  — Natural Earth 1:50m countries, release v5.1.2
The manifest (data/raw/grid/manifest.json, committed) records size, date and SHA-256.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import UTC, datetime

from db import ROOT
from download_data import download

GRID_DIR = ROOT / "data" / "raw" / "grid"

SOURCES = {
    "gistemp1200_GHCNv4_ERSSTv5.nc.gz": (
        "https://data.giss.nasa.gov/pub/gistemp/gistemp1200_GHCNv4_ERSSTv5.nc.gz",
        "NASA GISTEMP v4 monthly anomalies on a 2x2 degree grid (1200 km smoothing radius)",
    ),
    "ne_50m_admin_0_countries.geojson": (
        "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/v5.1.2/geojson/"
        "ne_50m_admin_0_countries.geojson",
        "Natural Earth 1:50m admin-0 countries, release v5.1.2 (public domain)",
    ),
}


def main() -> int:
    GRID_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {"downloaded_at": datetime.now(UTC).isoformat(timespec="seconds"), "files": {}}

    for name, (url, description) in SOURCES.items():
        try:
            content, last_modified = download(url)
        except OSError as error:
            print(f"ERROR  {name}: {error}", file=sys.stderr)
            return 1
        if content.lstrip()[:1] == b"<":
            print(f"ERROR  {name}: server returned HTML instead of data", file=sys.stderr)
            return 1
        (GRID_DIR / name).write_bytes(content)
        manifest["files"][name] = {
            "description": description,
            "url": url,
            "bytes": len(content),
            "last_modified": last_modified,
            "sha256": hashlib.sha256(content).hexdigest(),
        }
        print(f"OK     {name:<36} {len(content):>12,} bytes")

    (GRID_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("Manifest written to data/raw/grid/manifest.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
