"""Small units: SQL literal rendering, the sample-query library, the psql command builder."""

import re

import pandas as pd
import pytest

import queries as q
import setup_database as sd
from challenges import compare
from library import FILES, load_samples

# --- queries.render: the runnable copy shown under each chart --------------------------------

@pytest.mark.parametrize("value, literal", [
    (2024, "2024"),
    (0.5, "0.5"),
    (True, "TRUE"),
    ("GLB", "'GLB'"),
    ("O'Brien", "'O''Brien'"),                     # quotes are doubled, never left open
    (["GLB", "NH"], "ARRAY['GLB', 'NH']"),
])
def test_render_writes_valid_sql_literals(value, literal):
    assert q.render("SELECT %(x)s", {"x": value}) == f"SELECT {literal}"


def test_render_leaves_other_percent_signs_alone():
    assert q.render("SELECT 5 %% 2, %(x)s", {"x": 1}) == "SELECT 5 %% 2, 1"


# --- the sql/ library -----------------------------------------------------------------------

def test_sample_codes_are_unique_and_numbered_in_order():
    samples = load_samples()
    codes = [s.code for s in samples]
    assert len(codes) == len(set(codes))
    for prefix in {c[0] for c in codes}:
        numbers = [int(c[1:]) for c in codes if c[0] == prefix]
        assert numbers == list(range(1, len(numbers) + 1)), prefix


def test_every_library_file_is_loaded():
    levels = {s.level for s in load_samples()}
    assert levels == {level for _, level in FILES}


def test_each_sample_holds_exactly_one_query():
    for sample in load_samples():
        body = re.sub(r"--[^\n]*", "", sample.sql).strip()
        assert body.endswith(";") and body.count(";") == 1, sample.code


# --- challenges: ordered comparison ---------------------------------------------------------

def test_ordered_challenges_check_row_order():
    reference = pd.DataFrame({"year": [2024, 2023]})
    swapped = pd.DataFrame({"year": [2023, 2024]})
    assert compare(swapped, reference, ordered=False)[0]
    assert not compare(swapped, reference, ordered=True)[0]


# --- setup_database: docker vs local psql ---------------------------------------------------

def test_psql_command_uses_docker_by_default(monkeypatch):
    monkeypatch.delenv("PSQL_MODE", raising=False)
    command, _ = sd.psql_command(["-q"])
    assert command[:5] == ["docker", "compose", "exec", "-T", "db"]
    assert "ON_ERROR_STOP=1" in command


def test_psql_command_local_mode_passes_the_password_by_environment(monkeypatch):
    monkeypatch.setenv("PSQL_MODE", "local")
    monkeypatch.setattr(sd.shutil, "which", lambda _: "/usr/bin/psql")
    command, env = sd.psql_command([])
    assert command[0] == "psql" and "-h" in command
    assert env["PGPASSWORD"] and env["PGPASSWORD"] not in command    # never on the command line


def test_psql_command_local_mode_needs_a_client(monkeypatch):
    monkeypatch.setenv("PSQL_MODE", "local")
    monkeypatch.setattr(sd.shutil, "which", lambda _: None)
    with pytest.raises(SystemExit):
        sd.psql_command([])
