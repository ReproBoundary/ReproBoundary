#!/usr/bin/env python3
"""Run the released SynLogic converter and freeze the selected train rows."""

import json
import subprocess
from collections import Counter
from pathlib import Path

from datasets import Dataset


out = Path("data/synlogic")
out.mkdir(parents=True, exist_ok=True)
subprocess.run(
    ["python3", "src/logic_data_process.py", "--sub_set", "easy", "--local_dir", str(out)],
    check=True,
)
manifest = Path("REDUCTION_PROTOCOL/synlogic-easy-train-1024.ids.jsonl")
raw_ids = [json.loads(line)["id"] for line in manifest.read_text(encoding="utf-8").splitlines() if line.strip()]
prefix = "synlogic-easy-train:"
if any(not item.startswith(prefix) for item in raw_ids):
    raise SystemExit("unexpected SynLogic manifest ID")
indices = [int(item[len(prefix):]) for item in raw_ids]
if len(indices) != 1024 or len(set(indices)) != 1024:
    raise SystemExit("expected 1,024 unique SynLogic train indices")
dataset = Dataset.from_parquet(str(out / "train_easy.parquet"))
if max(indices) >= len(dataset):
    raise SystemExit("SynLogic manifest index exceeds the released training split")
dataset.select(indices).to_parquet(str(out / "train_easy_v4_1024.parquet"))
validation = Dataset.from_parquet(str(out / "test_easy.parquet"))
counts = Counter(str(source) for source in validation["data_source"])
counts_path = Path("artifacts/synlogic-validation-source-counts.json")
counts_path.parent.mkdir(parents=True, exist_ok=True)
counts_path.write_text(json.dumps(dict(sorted(counts.items())), indent=2) + "\n", encoding="utf-8")
