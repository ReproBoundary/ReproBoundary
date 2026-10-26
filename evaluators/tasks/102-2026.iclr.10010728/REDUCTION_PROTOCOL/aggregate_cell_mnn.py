#!/usr/bin/env python3
"""Aggregate the two released Multiome held-out-timepoint EMD results."""

import json
from pathlib import Path


values = []
sources = []
for day in (3, 4):
    candidates = sorted(
        Path("weights/mnn").glob(f"*skip_day{day}_*/test_results.json"),
        key=lambda path: path.stat().st_mtime,
    )
    if not candidates:
        raise SystemExit(f"missing test_results.json for held-out day {day}")
    source = candidates[-1]
    data = json.loads(source.read_text(encoding="utf-8"))
    emd = [(key, value) for key, value in data.items() if "emd" in key.lower()]
    if len(emd) != 1:
        raise SystemExit(f"expected one EMD value in {source}, found {emd}")
    values.append(float(emd[0][1]))
    sources.append(str(source))
payload = {"metric": "1-Wasserstein distance (EMD)", "held_out_values": values, "value": sum(values) / len(values), "sources": sources}
destination = Path("artifacts/multi-emd.json")
destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
