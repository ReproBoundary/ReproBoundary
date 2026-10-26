#!/usr/bin/env python3
"""Download, verify, and materialize the complete Hitori 5x5 subtask."""

import hashlib
import json
import urllib.request
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq


URL = (
    "https://huggingface.co/datasets/xhWu-fd/HardcoreLogic/resolve/"
    "d3d2185d289d4a2c1f67b8987dea37e26875ac3a/hardcore/Hitori_hardcore.parquet"
)
SHA256 = "15443e23cdad2b7d9aeb3e004a1bf201b6da6c8af768224085daf19ff1f016a4"


source = Path("data/hardcore/Hitori_hardcore.parquet")
source.parent.mkdir(parents=True, exist_ok=True)
if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest() != SHA256:
    urllib.request.urlretrieve(URL, source)
actual = hashlib.sha256(source.read_bytes()).hexdigest()
if actual != SHA256:
    raise SystemExit(f"HardcoreLogic parquet SHA256 mismatch: {actual}")
table = pq.read_table(source)
rows = [row for row in table.to_pylist() if str(row["id"]).startswith("gen-02--5x5-")]
manifest_ids = [json.loads(line)["id"] for line in Path(
    "REDUCTION_PROTOCOL/hitori-5x5-target.ids.jsonl"
).read_text(encoding="utf-8").splitlines() if line]
by_id = {str(row["id"]): row for row in rows}
if len(by_id) != 50 or list(by_id) != manifest_ids:
    raise SystemExit("released Hitori 5x5 IDs do not match the frozen canonical manifest")
target = source.with_name("hitori_hardcore.parquet")
pq.write_table(pa.Table.from_pylist([by_id[item] for item in manifest_ids]), target)
artifact = Path("artifacts/hardcorelogic-input.json")
artifact.parent.mkdir(parents=True, exist_ok=True)
artifact.write_text(json.dumps({
    "source_sha256": actual, "target_rows": 50,
    "canonical_ids_sha256": hashlib.sha256(Path(
        "REDUCTION_PROTOCOL/hitori-5x5-target.ids.jsonl"
    ).read_bytes()).hexdigest(),
}, indent=2) + "\n", encoding="utf-8")
