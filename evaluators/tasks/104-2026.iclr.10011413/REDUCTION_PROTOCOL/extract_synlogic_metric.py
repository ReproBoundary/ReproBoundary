#!/usr/bin/env python3
"""Extract the final full-SynLogic avg@8 accuracy from a DAPO console log."""

from collections import Counter
import json
import re
import sys
from pathlib import Path


log_path = Path(sys.argv[1])
output_path = Path(sys.argv[2])
counts_path = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("artifacts/synlogic-validation-source-counts.json")

# VERL emits one core mean per SynLogic game. Ignore val-aux statistics and
# other reward variants, and use only the final complete validation event.
pattern = re.compile(
    r"['\"]?(val-core/(.+?)/reward/mean@8)['\"]?\s*:\s*"
    r"(?:np\.float(?:32|64)\()?([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)"
)
events = []
for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
    values = {source: float(value) for _, source, value in pattern.findall(line)}
    if values:
        events.append(values)
if not events:
    raise SystemExit("could not locate val-core/<data-source>/reward/mean@8 in the DAPO log")

counts = Counter(json.loads(counts_path.read_text(encoding="utf-8")))
values = events[-1]
missing = sorted(set(counts) - set(values))
extra = sorted(set(values) - set(counts))
if missing or extra:
    raise SystemExit(f"validation source mismatch: missing={missing}, extra={extra}")
total = sum(counts.values())
if total <= 0:
    raise SystemExit("validation source counts are empty")
value = sum(values[source] * counts[source] for source in counts) / total * 100.0
output_path.parent.mkdir(parents=True, exist_ok=True)
output_path.write_text(json.dumps({
    "metric": "avg@8 accuracy",
    "unit": "percent",
    "value": value,
    "source_keys": sorted(f"val-core/{source}/reward/mean@8" for source in values),
    "source_prompt_counts": dict(sorted(counts.items())),
    "validation_event_count": len(events),
}, indent=2) + "\n", encoding="utf-8")
