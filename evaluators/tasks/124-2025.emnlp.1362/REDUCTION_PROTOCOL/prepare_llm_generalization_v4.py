#!/usr/bin/env python3
"""Materialize the repository-published frozen MMLU rewrites."""

import json
import subprocess
from pathlib import Path


FILE_ID = "15uxO5d8bJLFUV_1VFAsulH9H1DU9NySo"
target = Path("option_length/datasets/mmlu_rewrite")
archive = Path("option_length/datasets.tar.gz")
if not target.is_dir():
    archive.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["gdown", "--id", FILE_ID, "--output", str(archive)], check=True)
    subprocess.run(["tar", "-xzf", str(archive), "-C", "option_length"], check=True)
if not target.is_dir():
    raise SystemExit("released mmlu_rewrite dataset was not materialized")

from datasets import load_from_disk

subjects = sorted(path.name for path in target.iterdir() if path.is_dir())
test_count = 0
dev_count = 0
for subject in subjects:
    dataset = load_from_disk(str(target / subject))
    test_count += len(dataset["test"])
    dev_count += len(dataset["dev"])
if len(subjects) != 57 or test_count != 14042:
    raise SystemExit(f"expected 57 subjects and 14,042 tests, found {len(subjects)} and {test_count}")
artifact = Path("artifacts/llm-generalization-input.json")
artifact.parent.mkdir(parents=True, exist_ok=True)
artifact.write_text(json.dumps({
    "google_drive_file_id": FILE_ID, "subjects": len(subjects),
    "test_examples": test_count, "dev_examples": dev_count,
}, indent=2) + "\n", encoding="utf-8")
