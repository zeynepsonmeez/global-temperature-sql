"""Smoke tests for the Streamlit app (headless, via streamlit.testing.AppTest).

They need the database (they are skipped otherwise) and check that every page renders
without an exception, in both languages, and that the Playground runs and blocks queries.
"""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from database import database_available

ROOT = Path(__file__).resolve().parent.parent
MAIN = str(ROOT / "app" / "main.py")

pytestmark = pytest.mark.skipif(not database_available(), reason="database not available")


def open_page(page: str | None = None, lang: str = "en") -> AppTest:
    at = AppTest.from_file(MAIN, default_timeout=60)
    at.session_state["lang"] = lang
    at.run()
    if page:
        at.switch_page(page).run()
    assert not at.exception, at.exception
    return at


@pytest.mark.parametrize("lang", ["en", "tr"])
@pytest.mark.parametrize("page", [None, "views/explorer.py", "views/map.py", "views/playground.py"])
def test_pages_render(page, lang):
    open_page(page, lang)


def test_explorer_shows_kpis_and_tabs():
    at = open_page("views/explorer.py")
    assert len(at.metric) == 4
    assert len(at.tabs) == 7


def test_map_compares_countries_with_the_global_mean():
    at = open_page("views/map.py")
    at.multiselect(key="map_countries").set_value(["TUR", "DEU"]).run()
    assert not at.exception
    table = at.dataframe[-1].value
    assert len(table) == 3                                    # Türkiye, Germany, global mean
    at.multiselect(key="map_countries").set_value([]).run()  # nothing picked: global mean only
    assert not at.exception
    assert len(at.dataframe[-1].value) == 1


def test_playground_starts_with_an_empty_editor():
    at = open_page("views/playground.py")
    assert at.text_area[0].value == ""
    at.button[0].click().run()                      # running an empty editor
    assert at.error and "empty" in at.error[0].value.lower()


def test_playground_runs_a_query():
    at = open_page("views/playground.py")
    at.text_area[0].set_value("SELECT region, COUNT(*) AS n FROM v_monthly GROUP BY region ORDER BY region")
    at.button[0].click().run()
    assert not at.exception
    assert at.success, "expected a success message"
    frame = at.dataframe[0].value
    assert list(frame["region"]) == ["GLB", "NH", "SH"]


def test_playground_blocks_a_write():
    at = open_page("views/playground.py")
    at.text_area[0].set_value("DROP TABLE regions")
    at.button[0].click().run()
    assert at.error, "expected the query to be blocked"
    assert "read-only" in at.error[0].value.lower()


def test_playground_explains_a_database_error():
    at = open_page("views/playground.py")
    at.text_area[0].set_value("SELECT * FROM monthly_anomalies")   # base table: not visible to readers
    at.button[0].click().run()
    assert at.error
    assert "v_monthly" in at.error[0].value
