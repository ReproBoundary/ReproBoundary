#!/usr/bin/env python3
"""Extract ShapeX MCC-E ground-truth saliency AUPRC."""

import json
import math
import re
import sys
from pathlib import Path


source, destination = map(Path, sys.argv[1:3])
lines = [line for line in source.read_text(encoding="utf-8").splitlines() if line.startswith("mcce_")]
if not lines:
    raise SystemExit("no MCC-E ShapeX evaluation row was found")
matches = re.findall(r"(?:AUPRC|auprc):([0-9.eE+-]+)", lines[-1])
if len(matches) != 1:
    raise SystemExit("MCC-E row does not contain one AUPRC value")
value = float(matches[0])
if not math.isfinite(value) or not 0.0 <= value <= 1.0:
    raise SystemExit(f"invalid AUPRC: {value}")
payload = {
    "metric_id": "shapex_mcce_transformer_auprc",
    "metric": "AUPRC", "unit": "fraction", "value": value,
    "target_examples": 2000, "training_epochs": 10, "seed": 41,
    "source": str(source),
}
destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
print(json.dumps(payload, indent=2))
