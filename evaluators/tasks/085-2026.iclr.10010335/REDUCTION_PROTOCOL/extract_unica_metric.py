#!/usr/bin/env python3
"""Extract normalized MMSP MAE from the UniCA result table."""

import csv
import json
import math
import sys
from pathlib import Path


source, destination = map(Path, sys.argv[1:3])
with source.open(newline="", encoding="utf-8") as handle:
    rows = list(csv.DictReader(handle))
matching = [row for row in rows if row.get("dataset", "").lower() == "mmsp"]
if len(matching) != 1:
    raise SystemExit(f"expected one MMSP result, found {len(matching)}")
value = float(matching[0]["MAE_norm"])
if not math.isfinite(value) or not 0.0 <= value <= 1.0:
    raise SystemExit(f"invalid normalized MAE: {value}")
payload = {
    "metric_id": "unica_chronos_bolt_mmsp_mae", "metric": "MAE",
    "unit": "normalized_absolute_error", "value": value,
    "plants": 10, "epochs": 10, "batches_per_epoch": 20,
    "seed": 20260903, "source": str(source),
}
destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
print(json.dumps(payload, indent=2))
