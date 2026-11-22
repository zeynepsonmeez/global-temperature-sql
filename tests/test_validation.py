"""Each validation rule in clean_data.py must reject the problem it is written for."""

import pandas as pd
import pytest

import clean_data as cd


@pytest.fixture(scope="module")
def glb():
    wide = cd.read_wide_monthly(cd.RAW_DIR / cd.MONTHLY_FILES["GLB"])
    return wide, cd.to_long_monthly(wide, "GLB")


@pytest.mark.parametrize("break_it, message", [
    (lambda long: pd.concat([long, long.head(1)]), "duplicate"),
    (lambda long: long.assign(month=long.month.where(long.index != 5, 13)), "month outside"),
    (lambda long: long[long.year != 1950], "not contiguous"),
    (lambda long: long.assign(anomaly=long.anomaly.where(long.index != 5, 9.9)), "anomaly outside"),
])
def test_monthly_validation_rejects(glb, break_it, message):
    wide, long = glb
    with pytest.raises(ValueError, match=message):
        cd.validate_monthly(break_it(long.copy()), wide, "GLB")


def test_monthly_validation_rejects_a_wrong_annual_mean(glb):
    wide, long = glb
    tampered = wide.copy()
    tampered.loc[tampered.Year == 2000, "J-D"] += 0.5
    with pytest.raises(ValueError, match="J-D"):
        cd.validate_monthly(long, tampered, "GLB")


@pytest.fixture(scope="module")
def zonal():
    raw = pd.read_csv(cd.RAW_DIR / cd.ZONAL_FILE, na_values=cd.MISSING_MARKER)
    return raw, cd.read_zonal_long(cd.RAW_DIR / cd.ZONAL_FILE)


def test_zonal_validation_rejects_duplicates(zonal, glb):
    raw, long = zonal
    with pytest.raises(ValueError, match="duplicate"):
        cd.validate_zonal(pd.concat([long, long.head(1)]), raw, glb[0])


def test_zonal_validation_rejects_a_global_mismatch(zonal, glb):
    raw, long = zonal
    tampered = raw.copy()
    tampered.loc[tampered.Year == 2000, "Glob"] += 0.1
    with pytest.raises(ValueError, match="Glob"):
        cd.validate_zonal(long, tampered, glb[0])
