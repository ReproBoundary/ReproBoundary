#!/usr/bin/env python3
"""Normalize the official C-ARC test output into METRICS.json."""

import json
import sys
from pathlib import Path


source = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
candidates = [
    (key, value) for key, value in source.items()
    if "full_episode_acc" in key and isinstance(value, (int, float))
]
if len(candidates) != 1:
    raise SystemExit(f"expected one full_episode_acc value, found {candidates}")
key, raw = candidates[0]
value = float(raw) * 100.0 if float(raw) <= 1.0 else float(raw)
Path(sys.argv[2]).write_text(json.dumps({
    "metric": "exact match accuracy", "unit": "percent", "value": value,
    "official_key": key, "target_episodes": 8546,
}, indent=2) + "\n", encoding="utf-8")
