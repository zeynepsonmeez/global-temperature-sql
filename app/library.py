"""Read the sample queries from sql/*.sql so the Playground always shows the real library."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"
FILES = [("basic", "Basic"), ("intermediate", "Intermediate"), ("advanced", "Advanced"), ("spatial", "Spatial")]

# A query block starts with a header comment such as "-- B1. The 10 hottest months ..."
HEADER = re.compile(r"^-- ([BIAS]\d+)\. (.+)$", re.MULTILINE)


@dataclass(frozen=True)
class SampleQuery:
    code: str
    title: str
    level: str
    sql: str

    @property
    def label(self) -> str:
        return f"{self.code} · {self.title}"


def load_samples() -> list[SampleQuery]:
    samples: list[SampleQuery] = []
    for file_name, level in FILES:
        text = (SQL_DIR / f"{file_name}_queries.sql").read_text(encoding="utf-8")
        headers = list(HEADER.finditer(text))
        for i, header in enumerate(headers):
            end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
            block = text[header.start():end].strip()
            samples.append(SampleQuery(header.group(1), header.group(2).strip(), level, block))
    return samples
