"""Tests for the spatial data (grid, countries, PostGIS). Skipped until load_grid.py has run."""

import numpy as np
import pytest

from database import connect as reader_connect
from db import ROOT

GRID_FILE = ROOT / "data" / "raw" / "grid" / "gistemp1200_GHCNv4_ERSSTv5.nc.gz"


def scalar(cur, sql, params=None):
    cur.execute(sql, params)
    return cur.fetchone()[0]


def test_grid_has_16200_cells_covering_the_whole_sphere(grid_cur):
    assert scalar(grid_cur, "SELECT count(*) FROM grid_cells") == 16200
    assert scalar(grid_cur, "SELECT sum(area_weight) FROM grid_cells") == pytest.approx(1.0, abs=1e-9)
    # Equatorial cells are larger than polar cells: weight follows the cosine of latitude.
    equator = scalar(grid_cur, "SELECT area_weight FROM grid_cells WHERE lat = 1 LIMIT 1")
    polar = scalar(grid_cur, "SELECT area_weight FROM grid_cells WHERE lat = 89 LIMIT 1")
    assert equator / polar == pytest.approx(np.cos(np.radians(1)) / np.cos(np.radians(89)), rel=0.01)


def test_cell_geometry_is_valid_and_matches_the_centre(grid_cur):
    assert scalar(grid_cur, "SELECT bool_and(ST_IsValid(geom)) FROM grid_cells")
    off = scalar(grid_cur, "SELECT count(*) FROM grid_cells "
                      "WHERE NOT ST_Contains(geom, ST_SetSRID(ST_MakePoint(lon, lat), 4326))")
    assert off == 0


def test_grid_mean_reproduces_nasa_global_series(grid_cur):
    grid_cur.execute(
        """
        WITH grid AS (
            SELECT a.year, SUM(a.anomaly * g.area_weight) / SUM(g.area_weight) AS anomaly
            FROM   mv_grid_annual a JOIN grid_cells g USING (cell_id) GROUP BY a.year),
        official AS (
            SELECT year, AVG(anomaly) AS anomaly FROM v_monthly
            WHERE region = 'GLB' GROUP BY year HAVING COUNT(anomaly) = 12)
        SELECT AVG(ABS(g.anomaly - o.anomaly)), corr(g.anomaly, o.anomaly)
        FROM grid g JOIN official o USING (year) WHERE g.year >= 1950
        """
    )
    mean_diff, correlation = grid_cur.fetchone()
    assert float(mean_diff) < 0.02
    assert float(correlation) > 0.999


@pytest.mark.skipif(not GRID_FILE.exists(), reason="grid file not downloaded")
def test_storage_is_lossless_against_the_netcdf_file(grid_cur):
    """anomaly_c (SMALLINT hundredths) must equal NASA's int16 values exactly."""
    pytest.importorskip("xarray")
    from load_grid import open_grid
    with open_grid(GRID_FILE) as grid:
        month = grid["tempanomaly"].sel(time="2024-07").values.reshape(-1)
    expected = {cell + 1: int(v) for cell, v in enumerate(month) if v != 32767}
    grid_cur.execute("SELECT cell_id, anomaly_c FROM grid_anomalies WHERE obs_date = DATE '2024-07-01'")
    stored = dict(grid_cur.fetchall())
    assert stored == expected


def test_partition_pruning_reads_one_partition(grid_cur):
    grid_cur.execute("EXPLAIN (FORMAT JSON) SELECT * FROM grid_anomalies WHERE obs_date = DATE '2024-07-01'")
    plan = str(grid_cur.fetchone()[0])
    assert "grid_anomalies_2020" in plan
    assert "grid_anomalies_2010" not in plan and "grid_anomalies_1880" not in plan


def test_every_row_lives_in_its_decade_partition(grid_cur):
    grid_cur.execute(
        """
        SELECT count(*) FROM grid_anomalies
        WHERE tableoid::regclass::text <> 'grid_anomalies_' || (EXTRACT(YEAR FROM obs_date)::int / 10 * 10)
        """
    )
    assert grid_cur.fetchone()[0] == 0


def test_countries_and_overlaps_are_consistent(grid_cur):
    assert scalar(grid_cur, "SELECT count(*) FROM countries") > 200
    assert scalar(grid_cur, "SELECT bool_and(ST_IsValid(geom)) FROM countries")
    # A cell's overlap with a country can never exceed the cell's own area.
    too_big = scalar(grid_cur, """SELECT count(*) FROM cell_countries cc JOIN grid_cells g USING (cell_id)
                             WHERE cc.overlap_km2 > ST_Area(g.geom::geography) / 1e6 * 1.001""")
    assert too_big == 0


def test_turkiye_area_matches_reality(grid_cur):
    km2 = scalar(grid_cur, """SELECT SUM(overlap_km2) FROM cell_countries
                         JOIN countries USING (country_id) WHERE adm0_a3 = 'TUR'""")
    assert 760_000 < km2 < 800_000          # Türkiye: ~783,500 km2


def test_reader_can_use_postgis_through_the_playground(grid_cur):
    with reader_connect() as conn, conn.cursor() as reader:
        reader.execute("""SELECT name FROM countries
                          WHERE ST_Contains(geom, ST_SetSRID(ST_MakePoint(32.86, 39.93), 4326))""")
        assert reader.fetchone()[0] == "Turkey"
        reader.execute("SELECT count(*) FROM v_country_annual WHERE adm0_a3 = 'TUR'")
        assert reader.fetchone()[0] >= 10            # 146 years in full; 11 in CI (grid from 2015)
