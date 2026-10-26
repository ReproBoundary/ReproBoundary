#!/usr/bin/env python3
"""Extract the fixed 30-percent SciFact NDCG@10 result."""

import json
import math
import sys
from pathlib import Path


source, destination = map(Path, sys.argv[1:3])
result = json.loads(source.read_text(encoding="utf-8"))
try:
    value = float(result["metrics"]["by_percent"]["predictor"]["30"])
except (KeyError, TypeError, ValueError) as error:
    raise SystemExit("missing predictor NDCG@10 at the frozen 30% setting") from error
if not math.isfinite(value) or not 0.0 <= value <= 1.0:
    raise SystemExit(f"invalid NDCG@10: {value}")
payload = {
    "metric_id": "learning2select_qwen06b_scifact_ndcg10_30pct",
    "metric": "NDCG@10", "unit": "fraction", "value": value,
    "retained_dimensions_percent": 30, "target_queries": 300,
    "seed": 42, "source": str(source),
}
destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
print(json.dumps(payload, indent=2))
