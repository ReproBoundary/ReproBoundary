#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MAX_EVALUATOR_FILE_BYTES = 1024 * 1024
MAX_EVALUATOR_BUNDLE_BYTES = 10 * 1024 * 1024
DATASET_REPOSITORY = "SupingSun/ReproBoundary-Execution-Trajectories"
DATASET_REVISION = "57e17e11f795c6df9f7806ad2262fd32897ec2e6"
def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

errors = []
tasks = list(csv.DictReader((ROOT / "tasks/TASK_INVENTORY_47.csv").open(encoding="utf-8-sig")))
evaluators = list(csv.DictReader((ROOT / "evaluators/EVALUATOR_INDEX.csv").open()))
if len(tasks) != 47 or len({row["project_id"] for row in tasks}) != 47:
    errors.append("task inventory is not 47 unique projects")
if len(evaluators) != 47 or len({row["project_id"] for row in evaluators}) != 47:
    errors.append("evaluator index is not 47 unique projects")
bundled_logs = list(ROOT.rglob("*.gz"))
if bundled_logs:
    for path in bundled_logs[:10]:
        errors.append(f"trajectory log must be hosted externally: {path.relative_to(ROOT)}")

manifest = json.loads((ROOT / "RELEASE_MANIFEST.json").read_text())
if manifest.get("external_trajectory_count") != 423:
    errors.append("manifest external trajectory count is not 423")
if manifest.get("bundled_trajectory_file_count") != 0:
    errors.append("manifest bundled trajectory count is not zero")
if manifest.get("external_trajectory_repository") != DATASET_REPOSITORY:
    errors.append("manifest external trajectory repository does not match")
if manifest.get("external_trajectory_revision") != DATASET_REVISION:
    errors.append("manifest external trajectory revision does not match")

evaluator_files = [path for path in (ROOT / "evaluators").rglob("*") if path.is_file()]
evaluator_bundle_bytes = sum(path.stat().st_size for path in evaluator_files)
if evaluator_bundle_bytes > MAX_EVALUATOR_BUNDLE_BYTES:
    errors.append(f"evaluator bundle exceeds {MAX_EVALUATOR_BUNDLE_BYTES} bytes")
for path in evaluator_files:
    if path.stat().st_size > MAX_EVALUATOR_FILE_BYTES:
        errors.append(f"oversized evaluator file: {path.relative_to(ROOT)}")

for row in evaluators:
    task_dir = ROOT / "evaluators/tasks" / row["project_id"]
    contract = task_dir / "TARGET_EVALUATION.json"
    if not contract.is_file():
        errors.append(f"missing evaluator contract for {row['project_id']}")
        continue
    if sha256(contract) != row["contract_sha256"]:
        errors.append(f"evaluator contract hash mismatch for {row['project_id']}")
    helpers = [item for item in row["bundled_helper_files"].split(";") if item]
    actual_helpers = {
        str(path.relative_to(task_dir))
        for path in task_dir.rglob("*")
        if path.is_file() and path.name != "TARGET_EVALUATION.json"
    }
    if set(helpers) != actual_helpers:
        errors.append(f"evaluator helper index mismatch for {row['project_id']}")
    for helper in helpers:
        if not (task_dir / helper).is_file():
            errors.append(f"missing bundled evaluator file for {row['project_id']}: {helper}")

for raw in (ROOT / "SHA256SUMS").read_text().splitlines():
    expected, relative = raw.split("  ", 1)
    path = ROOT / relative
    if not path.is_file() or sha256(path) != expected:
        errors.append(f"package checksum mismatch: {relative}")

if errors:
    print("verification FAILED")
    for error in errors[:50]:
        print("-", error)
    raise SystemExit(1)
print(
    "verification OK: "
    f"tasks={len(tasks)} evaluators={len(evaluators)} "
    f"bundled_logs={len(bundled_logs)}"
)
