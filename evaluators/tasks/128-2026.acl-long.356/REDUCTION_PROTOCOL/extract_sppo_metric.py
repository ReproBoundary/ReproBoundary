#!/usr/bin/env python3
"""Extract the final MATH-500 Average@16 accuracy from a VERL log."""

import json
import re
import sys
from pathlib import Path


log_path = Path(sys.argv[1])
output_path = Path(sys.argv[2])
pattern = re.compile(
    r"['\"]?(val-core/math/acc/mean@16)['\"]?\s*:\s*"
    r"(?:np\.float(?:32|64)\()?([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)"
)
matches = pattern.findall(log_path.read_text(encoding="utf-8", errors="replace"))
if not matches:
    raise SystemExit("could not locate val-core/math/acc/mean@16 in the SPPO log")
key, raw = matches[-1]
value = float(raw) * 100.0
output_path.parent.mkdir(parents=True, exist_ok=True)
output_path.write_text(json.dumps({
    "metric": "Average@16 accuracy",
    "unit": "percent",
    "value": value,
    "source_key": key,
    "validation_event_count": len(matches),
}, indent=2) + "\n", encoding="utf-8")
