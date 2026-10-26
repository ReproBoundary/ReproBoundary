#!/usr/bin/env python3
"""Aggregate released Hitori evaluator verdicts into the frozen metric."""

import json
import sys
from pathlib import Path


rows = [json.loads(line) for line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines() if line]
if len(rows) != 200:
    raise SystemExit(f"expected 200 evaluated attempts, found {len(rows)}")
if len({row["id"] for row in rows}) != 50:
    raise SystemExit("expected 50 unique target puzzle IDs")
correct = sum(row.get("verdict") == 0 for row in rows)
Path(sys.argv[2]).write_text(json.dumps({
    "metric": "accuracy", "unit": "percent", "value": 100.0 * correct / len(rows),
    "correct_attempts": correct, "attempts": len(rows), "puzzles": 50,
}, indent=2) + "\n", encoding="utf-8")
