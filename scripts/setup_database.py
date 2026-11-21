"""Create (or re-create) the database schema and the read-only role.

Usage:
    python scripts/setup_database.py            # psql inside the Docker container (default)
    PSQL_MODE=local python scripts/setup_database.py   # a local psql client (used in CI)

Runs database/schema.sql, then database/roles.sql with the reader password from .env.
schema.sql drops existing tables, so run scripts/load_data.py afterwards.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

from db import ROOT, connection_settings

SCHEMA = ROOT / "database" / "schema.sql"
ROLES = ROOT / "database" / "roles.sql"


def psql_command(extra: list[str]) -> tuple[list[str], dict[str, str]]:
    settings = connection_settings()
    env = dict(os.environ)
    if os.getenv("PSQL_MODE", "docker") == "local":
        if not shutil.which("psql"):
            sys.exit("PSQL_MODE=local but no psql client was found on PATH")
        env["PGPASSWORD"] = settings["password"]
        base = ["psql", "-h", settings["host"], "-p", str(settings["port"]),
                "-U", settings["user"], "-d", settings["dbname"]]
    else:
        base = ["docker", "compose", "exec", "-T", "db",
                "psql", "-U", settings["user"], "-d", settings["dbname"]]
    return base + ["-v", "ON_ERROR_STOP=1", "-q", *extra], env


def run_file(path, extra: list[str] | None = None) -> None:
    command, env = psql_command(extra or [])
    with path.open("rb") as sql:
        completed = subprocess.run(command, stdin=sql, env=env, cwd=ROOT)
    if completed.returncode != 0:
        sys.exit(f"FAILED {path.relative_to(ROOT)}")
    print(f"OK     {path.relative_to(ROOT)}")


def main() -> int:
    reader_password = os.getenv("POSTGRES_READER_PASSWORD")
    if not reader_password:
        sys.exit("POSTGRES_READER_PASSWORD is not set (see .env.example)")
    run_file(SCHEMA)
    run_file(ROLES, ["-v", f"reader_password={reader_password}"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
