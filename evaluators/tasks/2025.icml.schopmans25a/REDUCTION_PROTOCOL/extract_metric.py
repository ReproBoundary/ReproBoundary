#!/usr/bin/env python3
"""Serialize the final official reverse-ESS stdout value on the paper's percent scale."""

import argparse
import json
import math
import re
from pathlib import Path


parser = argparse.ArgumentParser()
parser.add_argument("log", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()

pattern = re.compile(r"^ESS_None_1\.0K:\s*([-+0-9.eE]+)\s*$")
values = []
for line in args.log.read_text(encoding="utf-8", errors="replace").splitlines():
    match = pattern.match(line.strip())
    if match:
        values.append(float(match.group(1)))

if not values or not math.isfinite(values[-1]) or not 0.0 <= values[-1] <= 1.0:
    raise SystemExit("missing or invalid final ESS_None_1.0K value")

payload = {
    "metric_id": "2d_gmm_ta_bg_neural_splines_reverse_ess",
    "metric_name": "reverse effective sample size",
    "official_fraction": values[-1],
    "value_percent": 100.0 * values[-1],
    "evaluation_sample_count": 1000,
    "importance_weight_clipping_fraction": None,
    "direction": "maximize"
}
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
