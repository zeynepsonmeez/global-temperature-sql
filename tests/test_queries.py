"""Static checks on the app's own SQL (app/queries.py). No database needed."""

import re

import pytest

import queries as q

APP_QUERIES = {name: value for name, value in vars(q).items()
               if name.isupper() and isinstance(value, str) and "SELECT" in value}


@pytest.mark.parametrize("name", sorted(APP_QUERIES))
def test_no_stray_percent_signs(name):
    """psycopg treats every % in a parameterised query as a placeholder — even inside a
    SQL comment. Only %(name)s placeholders (or an escaped %%) are allowed."""
    stray = re.sub(r"%\(\w+\)s|%%", "", APP_QUERIES[name])
    assert "%" not in stray, f"{name} contains a bare '%'"


@pytest.mark.parametrize("name", sorted(APP_QUERIES))
def test_render_fills_every_placeholder(name):
    names = set(re.findall(r"%\((\w+)\)s", APP_QUERIES[name]))
    params = {key: ["GLB"] if key == "regions" else ("TUR" if key in ("region", "country") else 2000)
              for key in names}
    assert "%(" not in q.render(APP_QUERIES[name], params)
