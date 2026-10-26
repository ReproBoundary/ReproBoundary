#!/usr/bin/env python3
"""Extract the final frozen GLOT diagnostic accuracy."""

import json
import math
import re
import sys
from pathlib import Path


source, destination = map(Path, sys.argv[1:3])
matches = re.findall(r"Best Validation Accuracy:\s*([0-9.]+)", source.read_text(encoding="utf-8"))
if len(matches) != 1:
    raise SystemExit(f"expected one final GLOT accuracy, found {len(matches)}")
value = float(matches[0]) * 100.0
if not math.isfinite(value) or not 0.0 <= value <= 100.0:
    raise SystemExit(f"invalid accuracy: {value}")
payload = {
    "metric_id": "glot_bert_diagnostic_90pct_distractors_accuracy",
    "metric": "accuracy", "unit": "percent", "value": value,
    "training_examples": 1000, "target_examples": 2000,
    "distractor_ratio": 0.9, "seed": 0, "source": str(source),
}
destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
print(json.dumps(payload, indent=2))
