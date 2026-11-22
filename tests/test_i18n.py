"""Translation table checks: every text exists in both languages and is used correctly."""

import re
from pathlib import Path
from string import Formatter

import pytest

from i18n import MONTH_NAMES, TEXT

APP = Path(__file__).resolve().parent.parent / "app"


def placeholders(text: str) -> set[str]:
    return {field for _, field, _, _ in Formatter().parse(text) if field}


@pytest.mark.parametrize("key", sorted(TEXT))
def test_every_text_has_english_and_turkish(key):
    entry = TEXT[key]
    assert entry.get("en", "").strip() and entry.get("tr", "").strip()


@pytest.mark.parametrize("key", sorted(k for k, v in TEXT.items() if "{" in v["en"] + v["tr"]))
def test_placeholders_match_between_languages(key):
    """A {name} missing in one language would raise KeyError only when that language is used."""
    assert placeholders(TEXT[key]["en"]) == placeholders(TEXT[key]["tr"])


def test_every_key_used_in_the_code_exists():
    used = set()
    for path in APP.rglob("*.py"):
        used |= set(re.findall(r'\bt\(\s*"([a-z0-9_.]+)"', path.read_text(encoding="utf-8")))
    missing = used - set(TEXT)
    assert not missing, f"keys used in app/ but missing from TEXT: {sorted(missing)}"


def test_twelve_month_names_per_language():
    assert {lang: len(names) for lang, names in MONTH_NAMES.items()} == {"en": 12, "tr": 12}
