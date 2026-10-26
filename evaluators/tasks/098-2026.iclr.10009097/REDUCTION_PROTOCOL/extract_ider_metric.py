#!/usr/bin/env python3
"""Extract final five-task class-IL accuracy from an IDER console log."""

import ast
import json
import re
import sys
from pathlib import Path


text = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
matches = re.findall(r"evaluation acc:\s*\n(\[[^\n]+\])", text)
if not matches:
    raise SystemExit("no official evaluation acc block found")
values = [float(value) for value in ast.literal_eval(matches[-1])]
if len(values) != 5:
    raise SystemExit(f"expected final accuracies for five tasks, found {len(values)}")
Path(sys.argv[2]).write_text(json.dumps({
    "metric": "Final Average Accuracy", "unit": "percent",
    "value": sum(values) / len(values), "per_task_accuracy": values,
    "target_images": 10000, "training_seed": 0,
}, indent=2) + "\n", encoding="utf-8")
