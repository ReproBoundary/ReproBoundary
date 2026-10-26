#!/usr/bin/env python3
"""Extract the size-weighted frozen MMLU-WL exact-match result."""

import json
import sys
from pathlib import Path


source = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
key = "mmlu_rewrite_wrong1_generative"
result = source.get("results", {}).get(key, {})
value = result.get("exact_match,flexible-extract")
samples = source.get("n-samples", {})
total = sum(int(row.get("effective", 0)) for task, row in samples.items() if task.startswith(key + "_"))
if not isinstance(value, (int, float)) or total != 14042:
    raise SystemExit(f"invalid harness aggregate: value={value!r}, target_examples={total}")
Path(sys.argv[2]).write_text(json.dumps({
    "metric": "exact-match accuracy", "unit": "percent", "value": float(value) * 100.0,
    "target_examples": total, "task": key,
}, indent=2) + "\n", encoding="utf-8")
