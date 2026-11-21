"""Download NASA GISTEMP v4 tables into data/raw/ and record a manifest.

Usage:
    python scripts/download_data.py

The manifest (data/raw/manifest.json) stores when each file was downloaded,
its size, NASA's Last-Modified date and a SHA-256 checksum, so every analysis
can be traced back to the exact data snapshot it used.
"""

from __future__ import annotations

import hashlib
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE_URL = "https://data.giss.nasa.gov/gistemp/tabledata_v4"

# file name -> short description (kept in the manifest for documentation)
FILES = {
    "GLB.Ts+dSST.csv": "Global mean, monthly + seasonal + annual",
    "NH.Ts+dSST.csv": "Northern Hemisphere mean, monthly + seasonal + annual",
    "SH.Ts+dSST.csv": "Southern Hemisphere mean, monthly + seasonal + annual",
    "ZonAnn.Ts+dSST.csv": "Annual means for 8 latitude bands (zonal)",
}

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
TIMEOUT_SECONDS = 30


def download(url: str) -> tuple[bytes, str | None]:
    """Return the response body and the server's Last-Modified header."""
    request = urllib.request.Request(url, headers={"User-Agent": "global-temperature-sql"})
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return response.read(), response.headers.get("Last-Modified")


def main() -> int:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {
        "source": "NASA GISS Surface Temperature Analysis (GISTEMP v4)",
        "source_url": "https://data.giss.nasa.gov/gistemp/",
        "downloaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "files": {},
    }

    for name, description in FILES.items():
        url = f"{BASE_URL}/{name}"
        try:
            content, last_modified = download(url)
        except OSError as error:  # URLError, HTTPError and timeouts are all OSError
            print(f"ERROR  {name}: {error}", file=sys.stderr)
            return 1

        # A real CSV from NASA starts with a title line; an HTML error page does not.
        if content.lstrip().startswith(b"<"):
            print(f"ERROR  {name}: server returned HTML instead of CSV", file=sys.stderr)
            return 1

        (RAW_DIR / name).write_bytes(content)
        manifest["files"][name] = {
            "description": description,
            "url": url,
            "bytes": len(content),
            "last_modified": last_modified,
            "sha256": hashlib.sha256(content).hexdigest(),
        }
        print(f"OK     {name:<20} {len(content):>7,} bytes")

    manifest_path = RAW_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Manifest written to {manifest_path.relative_to(RAW_DIR.parent.parent)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
