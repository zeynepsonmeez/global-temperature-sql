"""Tests for the data-freshness check (no network: NASA's download is replaced by local bytes)."""

import pandas as pd
import pytest

import check_freshness as cf
import clean_data as cd


def long_table(rows):
    return pd.DataFrame(rows, columns=["year", "month", "anomaly"])


def test_compare_reports_added_and_revised_months():
    old = long_table([(2026, 9, 1.10), (2026, 10, 1.20)])
    new = long_table([(2026, 9, 1.13), (2026, 10, 1.20), (2026, 11, 1.25)])
    diff = cf.compare(old, new, ["year", "month"])
    assert diff.added == ["2026-11"]
    assert diff.removed == []
    assert diff.revised == 1
    assert diff.max_revision == pytest.approx(0.03)


def test_compare_ignores_rounding_and_counts_missing_values_as_revisions():
    old = long_table([(1990, 1, 0.40), (1990, 2, None)])
    new = long_table([(1990, 1, 0.404), (1990, 2, 0.35)])        # *** became a number
    diff = cf.compare(old, new, ["year", "month"])
    assert diff.revised == 1                                     # only the *** -> 0.35 change


def test_identical_tables_show_no_change():
    table = long_table([(2000, 1, 0.3), (2000, 2, 0.4)])
    diff = cf.compare(table, table.copy(), ["year", "month"])
    assert (diff.added, diff.removed, diff.revised) == ([], [], 0)


def serve(files: dict[str, bytes]):
    """A stand-in for download(): the given bytes, or the committed file."""
    def fake_download(url: str):
        name = url.rsplit("/", 1)[-1]
        return files.get(name, (cd.RAW_DIR / name).read_bytes()), "Thu, 10 Dec 2026 13:00:00 GMT"
    return fake_download


@pytest.fixture
def github(tmp_path, monkeypatch):
    summary, output = tmp_path / "summary.md", tmp_path / "output.txt"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    return summary, output


def test_unchanged_snapshot_is_up_to_date(monkeypatch, github):
    monkeypatch.setattr(cf, "download", serve({}))
    assert cf.main() == 0
    summary, output = github
    assert "up to date" in summary.read_text(encoding="utf-8")
    assert output.read_text(encoding="utf-8").strip() == "changed=false"


def test_a_new_release_is_described_without_touching_the_repository(monkeypatch, github):
    committed = (cd.RAW_DIR / "GLB.Ts+dSST.csv").read_bytes()
    lines = committed.decode().splitlines()
    last = len(lines) - 1
    lines[last] = lines[last].replace("***", ".99", 1)           # NASA publishes the next month
    release = ("\n".join(lines) + "\n").encode()
    monkeypatch.setattr(cf, "download", serve({"GLB.Ts+dSST.csv": release}))

    assert cf.main() == 0
    summary, output = github
    report = summary.read_text(encoding="utf-8")
    assert "newer GISTEMP release" in report
    assert "| `GLB.Ts+dSST.csv` | 1 added" in report
    assert output.read_text(encoding="utf-8").strip() == "changed=true"
    assert (cd.RAW_DIR / "GLB.Ts+dSST.csv").read_bytes() == committed   # check-only
