"""Benchmark indexing and partitioning strategies on the ~25M-row grid table.

Usage:
    python scripts/benchmark.py            # writes docs/benchmark_results.json

Method
  * A flat (non-partitioned) copy of grid_anomalies is built in a scratch schema, sorted by
    date like the original load, so every strategy sees the same physical data.
  * Each strategy adds ONE index to the flat copy (or uses the partitioned production
    table); the same four queries are run with EXPLAIN (ANALYZE, BUFFERS).
  * Every query runs once to warm the cache, then 5 times; the median execution time is
    reported, with the plan's main node and the number of table partitions it read.
  * The scratch schema is dropped at the end.
Absolute times depend on the machine; the ratios between strategies are the result.
"""

from __future__ import annotations

import json
import statistics
import sys
import time
from datetime import UTC, datetime

from db import ROOT, get_connection

RUNS = 5
OUT = ROOT / "docs" / "benchmark_results.json"

QUERIES = {
    "Q1_month_map": (
        "One month, every cell (the data behind a map)",
        "SELECT cell_id, anomaly_c FROM {t} WHERE obs_date = DATE '2024-07-01'",
    ),
    "Q2_global_mean_5y": (
        "Area-weighted global mean per year, 2020–2024",
        """SELECT EXTRACT(YEAR FROM a.obs_date) AS year,
                  SUM(a.anomaly_c * g.area_weight) / SUM(g.area_weight) / 100 AS anomaly
           FROM {t} a JOIN grid_cells g USING (cell_id)
           WHERE a.obs_date >= DATE '2020-01-01' AND a.obs_date < DATE '2025-01-01'
           GROUP BY 1""",
    ),
    "Q3_one_cell_series": (
        "Full monthly history of one cell (Ankara)",
        "SELECT obs_date, anomaly_c FROM {t} WHERE cell_id = 11627 ORDER BY obs_date",
    ),
    "Q4_country_series": (
        "Türkiye: monthly area-weighted series from the raw grid",
        """SELECT a.obs_date, SUM(a.anomaly_c * cc.overlap_km2) / SUM(cc.overlap_km2) / 100 AS anomaly
           FROM {t} a
           JOIN cell_countries cc USING (cell_id)
           JOIN countries c USING (country_id)
           WHERE c.adm0_a3 = 'TUR'
           GROUP BY a.obs_date""",
    ),
}

# name, description, table, index DDL (None = no extra index)
STRATEGIES = [
    ("flat_no_index", "Flat table, no index", "bench.flat", None),
    ("flat_btree_date", "Flat + B-tree (obs_date)", "bench.flat",
     "CREATE INDEX flat_btree_date ON bench.flat (obs_date)"),
    ("flat_brin_date", "Flat + BRIN (obs_date)", "bench.flat",
     "CREATE INDEX flat_brin_date ON bench.flat USING brin (obs_date)"),
    ("flat_btree_cell_date", "Flat + B-tree (cell_id, obs_date)", "bench.flat",
     "CREATE INDEX flat_btree_cell_date ON bench.flat (cell_id, obs_date)"),
    ("partitioned", "Partitioned by decade + PK (cell_id, obs_date) + BRIN — production", "grid_anomalies", None),
]

MATVIEW_QUERY = ("Türkiye: annual series from the materialized view",
                 "SELECT year, anomaly FROM v_country_annual WHERE adm0_a3 = 'TUR'")


def walk(plan: dict):
    yield plan
    for child in plan.get("Plans", []):
        yield from walk(child)


def measure(cur, sql: str) -> dict:
    cur.execute("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + sql)          # warm-up
    times = []
    for _ in range(RUNS):
        cur.execute("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + sql)
        result = cur.fetchone()[0][0]
        times.append(result["Execution Time"])
    nodes = list(walk(result["Plan"]))
    scans = [n for n in nodes if "Relation Name" in n and n["Relation Name"].startswith(("grid_anomalies", "flat"))]
    main = next((n["Node Type"] for n in nodes
                 if n["Node Type"] in ("Seq Scan", "Parallel Seq Scan", "Index Scan", "Index Only Scan",
                                       "Bitmap Heap Scan", "Parallel Bitmap Heap Scan", "Parallel Index Scan",
                                       "Parallel Index Only Scan")
                 and n.get("Relation Name", "").startswith(("grid_anomalies", "flat"))), "-")
    return {
        "median_ms": round(statistics.median(times), 2),
        "min_ms": round(min(times), 2),
        "scan": main,
        "partitions_read": len({n["Relation Name"] for n in scans}),
        "shared_buffers_read": sum(n.get("Shared Read Blocks", 0) + n.get("Shared Hit Blocks", 0) for n in scans),
    }


def relation_size(cur, name: str) -> int:
    cur.execute("SELECT pg_relation_size(%s::regclass)", (name,))
    return cur.fetchone()[0]


def main() -> int:
    results = {"generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
               "runs_per_query": RUNS, "queries": {k: v[0] for k, v in QUERIES.items()},
               "strategies": [], "materialized_view": None}

    with get_connection(autocommit=True) as conn, conn.cursor() as cur:
        cur.execute("SET search_path = public, postgis")
        cur.execute("SELECT version()")
        results["postgres"] = cur.fetchone()[0].split(" on ")[0]

        print("...    building flat copy (sorted by date)", flush=True)
        cur.execute("DROP SCHEMA IF EXISTS bench CASCADE")
        cur.execute("CREATE SCHEMA bench")
        started = time.perf_counter()
        cur.execute("CREATE TABLE bench.flat AS SELECT * FROM grid_anomalies ORDER BY obs_date, cell_id")
        cur.execute("VACUUM ANALYZE bench.flat")
        results["flat_table"] = {"build_s": round(time.perf_counter() - started, 1),
                                 "size_bytes": relation_size(cur, "bench.flat")}
        cur.execute("SELECT count(*) FROM bench.flat")
        results["rows"] = cur.fetchone()[0]

        try:
            for name, description, table, ddl in STRATEGIES:
                entry = {"name": name, "description": description, "queries": {}}
                if ddl:
                    started = time.perf_counter()
                    cur.execute(ddl)
                    entry["index_build_s"] = round(time.perf_counter() - started, 1)
                    entry["index_size_bytes"] = relation_size(cur, "bench." + ddl.split()[2])
                    cur.execute("ANALYZE bench.flat")
                for key, (_, sql) in QUERIES.items():
                    entry["queries"][key] = measure(cur, sql.format(t=table))
                    m = entry["queries"][key]
                    print(f"OK     {name:<22} {key:<20} {m['median_ms']:>10,.1f} ms  {m['scan']}"
                          f"  ({m['partitions_read']} relation(s))", flush=True)
                if ddl:
                    cur.execute(f"DROP INDEX bench.{ddl.split()[2]}")
                results["strategies"].append(entry)

            results["materialized_view"] = {"description": MATVIEW_QUERY[0], **measure(cur, MATVIEW_QUERY[1])}
            print(f"OK     materialized view      Q4                   "
                  f"{results['materialized_view']['median_ms']:>10,.1f} ms", flush=True)
        finally:
            cur.execute("DROP SCHEMA IF EXISTS bench CASCADE")

    OUT.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"Results written to {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
