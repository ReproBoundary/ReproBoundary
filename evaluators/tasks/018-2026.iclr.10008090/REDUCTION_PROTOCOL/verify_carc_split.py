#!/usr/bin/env python3
"""Verify the C-ARC split counts and frozen first-4096 training selection."""

import json
from pathlib import Path


root = Path("data/split_seed_1860")
expected = {"train": 4096, "val": 8546, "test": 8546}
for split, count in expected.items():
    path = root / f"{split}_systematicity_seed_1860.jsonl"
    rows = path.read_text(encoding="utf-8").splitlines()
    if len(rows) != count:
        raise SystemExit(f"{split}: expected {count} rows, found {len(rows)}")
manifest = Path("REDUCTION_PROTOCOL/carc-train-4096.ids.jsonl")
ids = [json.loads(line)["id"] for line in manifest.read_text().splitlines() if line]
expected_ids = [f"systematicity_seed_1860/train/{index:06d}" for index in range(4096)]
if ids != expected_ids:
    raise SystemExit("C-ARC training-position manifest mismatch")
