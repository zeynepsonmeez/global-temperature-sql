"""Check whether NASA has published a newer GISTEMP release than the committed snapshot.

Usage:
    python scripts/check_freshness.py

Check-only: the current files are downloaded into a temporary folder and compared with
data/raw/manifest.json and the committed CSVs. Nothing in the repository changes. The report
lists, per file, the months (or years) NASA added and the past values it revised.

On GitHub Actions the report is also written to the job summary, and `changed=true|false`
to the step outputs, so the data-freshness workflow can re-check the README findings.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

import clean_data as cd
from download_data import BASE_URL, FILES, download

MANIFEST = cd.RAW_DIR / "manifest.json"
REVISION_TOLERANCE = 0.005          # values are published with 2 decimals


@dataclass
class Diff:
    added: list[str]                # periods present only in the new file, e.g. "2026-11"
    removed: list[str]              # periods present only in the committed file
    revised: int                    # periods present in both whose value changed
    max_revision: float             # largest absolute change, °C


def compare(old: pd.DataFrame, new: pd.DataFrame, keys: list[str]) -> Diff:
    """Compare two long tables (keys + anomaly) and describe what changed."""
    merged = old.merge(new, on=keys, how="outer", suffixes=("_old", "_new"), indicator=True)

    def label(row) -> str:
        return "-".join(f"{int(row[k]):02d}" if k == "month" else str(row[k]) for k in keys)

    added = [label(r) for _, r in merged[merged["_merge"] == "right_only"].iterrows()]
    removed = [label(r) for _, r in merged[merged["_merge"] == "left_only"].iterrows()]
    both = merged[merged["_merge"] == "both"]
    change = (both["anomaly_new"] - both["anomaly_old"]).abs()
    # A value that appears or disappears (*** <-> number) is a revision too.
    flipped = both["anomaly_new"].isna() != both["anomaly_old"].isna()
    revised = int(((change > REVISION_TOLERANCE) | flipped).sum())
    return Diff(added, removed, revised, float(change.max()) if change.notna().any() else 0.0)


def monthly_long(path: Path, code: str) -> pd.DataFrame:
    return cd.to_long_monthly(cd.read_wide_monthly(path), code)


def zonal_long(path: Path) -> pd.DataFrame:
    return cd.read_zonal_long(path)


def describe(name: str, diff: Diff) -> str:
    parts = []
    if diff.added:
        shown = diff.added if len(diff.added) <= 3 else [*diff.added[:1], "…", diff.added[-1]]
        parts.append(f"{len(diff.added)} added ({', '.join(shown)})")
    if diff.removed:
        parts.append(f"{len(diff.removed)} removed")
    if diff.revised:
        parts.append(f"{diff.revised} revised (max {diff.max_revision:.2f} °C)")
    return f"| `{name}` | {'; '.join(parts) or 'same values, file re-published'} |"


def write_github(report: str, changed: bool) -> None:
    if summary := os.getenv("GITHUB_STEP_SUMMARY"):
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(report + "\n")
    if output := os.getenv("GITHUB_OUTPUT"):
        with open(output, "a", encoding="utf-8") as fh:
            fh.write(f"changed={'true' if changed else 'false'}\n")


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    rows, newest = [], None
    with tempfile.TemporaryDirectory() as tmp:
        for name in FILES:
            try:
                content, last_modified = download(f"{BASE_URL}/{name}")
            except OSError as error:
                print(f"ERROR  {name}: {error}", file=sys.stderr)
                return 1
            newest = newest or last_modified
            if hashlib.sha256(content).hexdigest() == manifest["files"][name]["sha256"]:
                continue
            fresh = Path(tmp) / name
            fresh.write_bytes(content)
            committed = cd.RAW_DIR / name
            if name == cd.ZONAL_FILE:
                diff = compare(zonal_long(committed), zonal_long(fresh), ["region_code", "year"])
            else:
                code = next(c for c, f in cd.MONTHLY_FILES.items() if f == name)
                diff = compare(monthly_long(committed, code), monthly_long(fresh, code), ["year", "month"])
            rows.append(describe(name, diff))

    snapshot = manifest["files"]["GLB.Ts+dSST.csv"]["last_modified"]
    if rows:
        report = "\n".join([
            "## NASA has published a newer GISTEMP release",
            "",
            f"Committed snapshot: **{snapshot}** · NASA now: **{newest}**",
            "",
            "| File | Change |",
            "|---|---|",
            *rows,
            "",
            "Nothing was changed in the repository. To adopt the release: run `download_data.py`, "
            "`clean_data.py` and the load scripts, then `pytest tests/test_findings.py`, and update "
            "the README findings and snapshot date if a test fails.",
        ])
    else:
        report = f"## GISTEMP is up to date\n\nThe committed snapshot (**{snapshot}**) matches NASA's files."
    print(report)
    write_github(report, changed=bool(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
