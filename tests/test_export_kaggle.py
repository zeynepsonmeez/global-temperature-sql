"""The Kaggle export writes every file, a description that matches them and valid metadata."""

import json

import pandas as pd

import export_kaggle as ek


def test_export_writes_every_file_and_a_matching_description(admin_conn, tmp_path):
    rows = ek.export(tmp_path)

    assert set(rows) == {e.name for e in ek.EXPORTS}
    for e in ek.EXPORTS:
        path = tmp_path / e.name
        frame = pd.read_parquet(path) if e.name.endswith(".parquet") else pd.read_csv(path)
        assert list(frame.columns) == list(e.columns), e.name        # the description lists every column
        assert len(frame) == rows[e.name]

    with admin_conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM v_monthly")
        assert rows["monthly_global.csv"] == cur.fetchone()[0]
    admin_conn.rollback()

    readme = (tmp_path / "README.md").read_text(encoding="utf-8")
    assert f"| `monthly_global.csv` | {rows['monthly_global.csv']:,} |" in readme
    assert "Lenssen" in readme and ek.REPO_URL in readme


def test_metadata_fits_kaggle_limits(admin_conn, tmp_path):
    ek.export(tmp_path, include_grid=False)
    meta = json.loads((tmp_path / "dataset-metadata.json").read_text(encoding="utf-8"))
    assert 6 <= len(meta["title"]) <= 50                # Kaggle's limits for a dataset title
    assert 20 <= len(meta["subtitle"]) <= 80            # and subtitle
    assert meta["id"] == ek.KAGGLE_ID
    assert not (tmp_path / "grid_annual.parquet").exists()
