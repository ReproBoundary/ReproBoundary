#!/usr/bin/env python3
"""Extract the final MAP city baseline accuracy."""

import json
import math
import re
import sys
from pathlib import Path


source, destination = map(Path, sys.argv[1:3])
text = source.read_text(encoding="utf-8")
matches = re.findall(r"BASELINE\s*:\s*loss\s+[0-9.eE+-]+\s+acc\s+([0-9.]+)%", text)
if len(matches) != 1:
    raise SystemExit(f"expected one baseline accuracy, found {len(matches)}")
value = float(matches[0])
if not math.isfinite(value) or not 0.0 <= value <= 100.0:
    raise SystemExit(f"invalid accuracy: {value}")
payload = {
    "metric_id": "value_coding_city_map_baseline_accuracy",
    "metric": "accuracy", "unit": "percent", "value": value,
    "training_pairs": 70000, "target_pairs": 175000, "seed": 42,
    "source": str(source),
}
destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
print(json.dumps(payload, indent=2))
