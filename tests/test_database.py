"""Database tests. They need the Docker database running and loaded:

    docker compose up -d
    python scripts/load_data.py
    pytest

If the database is not reachable, these tests are skipped (the data tests still run).
"""

import psycopg
import pytest

import clean_data as cd
from db import get_connection


@pytest.fixture(scope="module")
def conn():
    try:
        connection = get_connection()
    except (psycopg.OperationalError, RuntimeError) as error:
        pytest.skip(f"database not available: {error}")
    yield connection
    connection.close()


@pytest.fixture
def cur(conn):
    """Each test runs inside a transaction that is rolled back afterwards."""
    with conn.cursor() as cursor:
        yield cursor
    conn.rollback()


def scalar(cur, sql, params=None):
    cur.execute(sql, params)
    return cur.fetchone()[0]


def test_row_counts_match_processed_files(cur):
    def data_rows(name: str) -> int:          # lines minus the header
        return len((cd.PROCESSED_DIR / name).read_text(encoding="utf-8").splitlines()) - 1

    monthly = data_rows("monthly_anomalies.csv")
    zonal = data_rows("zonal_annual_anomalies.csv")
    assert scalar(cur, "SELECT count(*) FROM v_monthly") == monthly
    assert scalar(cur, "SELECT count(*) FROM v_annual") == zonal


def test_sql_annual_mean_matches_nasa_j_d(cur):
    """Our annual means, computed in SQL, must agree with NASA's published J-D column."""
    cur.execute(
        """
        SELECT year, AVG(anomaly)
        FROM   v_monthly
        WHERE  region = 'GLB'
        GROUP  BY year
        HAVING COUNT(anomaly) = 12
        """
    )
    sql_annual = {year: float(value) for year, value in cur.fetchall()}
    nasa = cd.read_wide_monthly(cd.RAW_DIR / cd.MONTHLY_FILES["GLB"]).dropna(subset=["J-D"])
    nasa_annual = dict(zip(nasa["Year"], nasa["J-D"], strict=True))

    assert sql_annual.keys() == nasa_annual.keys()
    worst = max(abs(sql_annual[y] - nasa_annual[y]) for y in sql_annual)
    assert worst <= 0.01


def test_baseline_period_averages_to_zero_in_sql(cur):
    value = scalar(cur, "SELECT AVG(anomaly) FROM v_monthly WHERE year BETWEEN 1951 AND 1980")
    assert abs(float(value)) < 0.01


def test_obs_date_is_generated(cur):
    cur.execute("SELECT obs_date FROM v_monthly WHERE region = 'GLB' AND year = 1880 AND month = 3")
    assert str(cur.fetchone()[0]) == "1880-03-01"


def test_latest_view_points_to_newest_snapshot(cur):
    latest = scalar(cur, "SELECT dataset_id FROM v_latest_dataset")
    # Other snapshots (the spatial grid) are also in datasets: the view must ignore them.
    newest = scalar(cur, "SELECT dataset_id FROM datasets WHERE name = 'GISTEMP v4' "
                         "ORDER BY downloaded_at DESC LIMIT 1")
    assert latest == newest


@pytest.mark.parametrize(
    "bad_row, error, message",
    [
        # Month 13 never reaches the CHECK: the generated column obs_date = make_date(...)
        # is computed first and fails, so PostgreSQL reports a date overflow instead.
        ((2000, 13, 0.5), psycopg.errors.DatetimeFieldOverflow, "out of range"),
        ((1850, 1, 0.5), psycopg.errors.CheckViolation, "monthly_year_valid"),
        ((2000, 1, 123.45), psycopg.errors.NumericValueOutOfRange, "numeric field overflow"),
    ],
)
def test_invalid_rows_are_rejected(cur, bad_row, error, message):
    with pytest.raises(error, match=message):
        cur.execute(
            """
            INSERT INTO monthly_anomalies (dataset_id, region_id, year, month, anomaly)
            SELECT (SELECT dataset_id FROM v_latest_dataset),
                   (SELECT region_id FROM regions WHERE code = 'GLB'), %s, %s, %s
            """,
            bad_row,
        )


def test_primary_key_rejects_duplicate_month(cur):
    with pytest.raises(psycopg.errors.UniqueViolation):
        cur.execute(
            """
            INSERT INTO monthly_anomalies (dataset_id, region_id, year, month, anomaly)
            SELECT dataset_id, region_id, year, month, anomaly
            FROM   monthly_anomalies
            LIMIT  1
            """
        )


def test_anomaly_column_accepts_null(cur):
    cur.execute(
        """
        INSERT INTO monthly_anomalies (dataset_id, region_id, year, month, anomaly)
        SELECT (SELECT dataset_id FROM v_latest_dataset),
               (SELECT region_id FROM regions WHERE code = 'GLB'), 2999, 1, NULL
        """
    )
    assert scalar(cur, "SELECT anomaly FROM monthly_anomalies WHERE year = 2999") is None


@pytest.mark.parametrize("name", ["basic", "intermediate", "advanced", "spatial", "drivers"])
def test_sql_library_runs(cur, name):
    """Every query in sql/*.sql must keep running as the schema evolves."""
    sql = (cd.ROOT / "sql" / f"{name}_queries.sql").read_text(encoding="utf-8")
    cur.execute(sql)  # several statements in one call; raises on the first error


def test_foreign_key_rejects_unknown_region(cur):
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        cur.execute(
            """
            INSERT INTO monthly_anomalies (dataset_id, region_id, year, month, anomaly)
            VALUES ((SELECT dataset_id FROM v_latest_dataset), 9999, 2000, 1, 0.1)
            """
        )
