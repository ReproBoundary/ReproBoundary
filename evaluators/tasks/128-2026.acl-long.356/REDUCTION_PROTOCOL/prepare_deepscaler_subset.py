#!/usr/bin/env python3
"""Filter DeepScaler-Math by the frozen extra_info.index manifest."""

import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq


source = Path("data/deepscaler-math.parquet")
manifest = Path("REDUCTION_PROTOCOL/deepscaler-train-512.ids.jsonl")
raw_ids = [json.loads(line)["id"] for line in manifest.read_text(encoding="utf-8").splitlines() if line.strip()]
prefix = "deepscaler:"
if any(not item.startswith(prefix) for item in raw_ids):
    raise SystemExit("unexpected DeepScaler manifest ID")
wanted = {item[len(prefix):] for item in raw_ids}
table = pq.read_table(source)
rows = table.to_pylist()
selected = [row for row in rows if str(row["extra_info"]["index"]) in wanted]
found = {str(row["extra_info"]["index"]) for row in selected}
if len(selected) != 512 or found != wanted:
    raise SystemExit(f"DeepScaler manifest mismatch: selected={len(selected)}, missing={len(wanted - found)}")
pq.write_table(pa.Table.from_pylist(selected, schema=table.schema), "data/deepscaler-math-v4-512.parquet")

