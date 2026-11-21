"""Data tests: run with `pytest` from the project root."""

import pandas as pd
import pytest

import clean_data as cd


@pytest.fixture(scope="module")
def glb_wide():
    return cd.read_wide_monthly(cd.RAW_DIR / cd.MONTHLY_FILES["GLB"])


@pytest.fixture(scope="module")
def glb_long(glb_wide):
    return cd.to_long_monthly(glb_wide, "GLB")


def test_missing_marker_becomes_null_not_zero(tmp_path):
    csv = tmp_path / "tiny.csv"
    csv.write_text(
        "Title line\n"
        "Year," + ",".join(cd.MONTHS) + ",J-D\n"
        "2000," + ",".join(["***"] + [".10"] * 11) + ",***\n"
    )
    wide = cd.read_wide_monthly(csv)
    assert pd.isna(wide.loc[0, "Jan"])
    assert wide.loc[0, "Feb"] == pytest.approx(0.10)


def test_gap_in_middle_is_kept_as_null(tmp_path):
    csv = tmp_path / "gap.csv"
    csv.write_text(
        "Title line\n"
        "Year," + ",".join(cd.MONTHS) + "\n"
        "2000," + ",".join([".10"] * 5 + ["***"] + [".10"] * 6) + "\n"
    )
    long = cd.to_long_monthly(cd.read_wide_monthly(csv), "GLB")
    assert len(long) == 12
    assert long["anomaly"].isna().sum() == 1


def test_long_format_shape(glb_wide, glb_long):
    # Every published month appears exactly once; only not-yet-published months are missing.
    assert not glb_long.duplicated(["year", "month"]).any()
    assert set(glb_long["month"]) == set(range(1, 13))
    expected = glb_wide[cd.MONTHS].notna().sum().sum()
    assert len(glb_long) == expected


def test_starts_in_1880(glb_long):
    first = glb_long.iloc[0]
    assert (first["year"], first["month"]) == (1880, 1)


def test_no_future_months(glb_long):
    last = glb_long.iloc[-1]
    assert pd.notna(last["anomaly"])


@pytest.mark.parametrize("code", ["GLB", "NH", "SH"])
def test_validation_passes_on_real_data(code):
    wide = cd.read_wide_monthly(cd.RAW_DIR / cd.MONTHLY_FILES[code])
    cd.validate_monthly(cd.to_long_monthly(wide, code), wide, code)


def test_baseline_period_averages_to_zero(glb_long):
    base = glb_long[glb_long["year"].between(1951, 1980)]["anomaly"].mean()
    assert abs(base) < 0.01


def test_validation_catches_shifted_values(glb_wide):
    broken = glb_wide.copy()
    broken[cd.MONTHS] = broken[cd.MONTHS] + 0.5  # simulate a wrong baseline
    with pytest.raises(ValueError):
        cd.validate_monthly(cd.to_long_monthly(broken, "GLB"), broken, "GLB")


def test_zonal_has_all_bands():
    zonal = cd.read_zonal_long(cd.RAW_DIR / cd.ZONAL_FILE)
    assert set(zonal["region_code"]) == set(cd.ZONAL_CODES)
    assert not zonal.duplicated(["region_code", "year"]).any()


def test_zonal_global_matches_glb_annual(glb_wide):
    zonal_raw = pd.read_csv(cd.RAW_DIR / cd.ZONAL_FILE, na_values=cd.MISSING_MARKER)
    zonal = cd.read_zonal_long(cd.RAW_DIR / cd.ZONAL_FILE)
    cd.validate_zonal(zonal, zonal_raw, glb_wide)


def test_regions_are_consistent():
    regions = cd.regions_frame()
    assert regions["code"].is_unique
    assert (regions["lat_min"] < regions["lat_max"]).all()
    # The 8 narrow bands tile the globe from pole to pole with no gaps.
    bands = regions[regions["kind"] == "zonal"].sort_values("lat_min")
    assert bands["lat_min"].iloc[0] == -90 and bands["lat_max"].iloc[-1] == 90
    assert (bands["lat_max"].iloc[:-1].values == bands["lat_min"].iloc[1:].values).all()
