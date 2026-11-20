#!/usr/bin/env python3
"""Measure parse cost and snapshot size; rewrite identity.json.

Run from the repository root: python3 docs/bench/identity.py
"""
import importlib.util
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def module():
    spec = importlib.util.spec_from_file_location("process_birth", ROOT / "process_birth.py")
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def bench(call, runs=9):
    values = []
    for _ in range(runs):
        start = time.perf_counter()
        call()
        values.append((time.perf_counter() - start) * 1e6)
    values.sort()
    return values[0], values[len(values) // 2]


def main():
    birth = module()
    sample = "Sat Sep 26 11:54:39 2026"
    low, mid = bench(lambda: birth.epoch(sample, legacy_zone="UTC"), runs=2000)
    start = time.perf_counter()
    rows = birth.snapshot()
    snapshot_ms = (time.perf_counter() - start) * 1000
    data = {
        "schema": "process-birth-bench/1",
        "date": time.strftime("%Y-%m-%d"),
        "host": "macOS arm64 (Apple M5 Pro)",
        "python": ".".join(map(str, __import__("sys").version_info[:3])),
        "epoch_parse_us_min": round(low, 2),
        "epoch_parse_us_median": round(mid, 2),
        "snapshot_rows": len(rows),
        "snapshot_ms": round(snapshot_ms, 1),
        "invalid_values_return_none": birth.epoch("not a date") is None and birth.read(-1) is None,
        "missing_observations_match": birth.same(None, None),
    }
    # Only an explicit --write replaces the committed measurement.
    if "--write" in __import__("sys").argv[1:]:
        (ROOT / "docs/bench/identity.json").write_text(json.dumps(data, indent=2) + "\n")
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
