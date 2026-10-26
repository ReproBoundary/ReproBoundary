#!/usr/bin/env python3
"""Convert the frozen AlignFlow FID CSV into the benchmark metric artifact."""

import csv
import json
import math
import sys
from pathlib import Path


source = Path(sys.argv[1])
destination = Path(sys.argv[2])
with source.open(newline="", encoding="utf-8") as handle:
    rows = list(csv.DictReader(handle))
if len(rows) != 1:
    raise SystemExit(f"expected exactly one FID row, found {len(rows)}")
value = float(rows[0]["fid-50k"])
if not math.isfinite(value) or value < 0:
    raise SystemExit(f"invalid FID value: {value}")
destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_text(json.dumps({
    "metric": "FID-50K",
    "unit": "FID",
    "value": value,
    "checkpoint": rows[0]["path"],
    "generated_images": 50000,
    "ode_solver": "DOPRI5",
    "generation_seed": 0,
}, indent=2) + "\n", encoding="utf-8")
