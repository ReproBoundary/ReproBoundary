#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_EVALUATOR_FILE_BYTES = 1024 * 1024
MAX_EVALUATOR_BUNDLE_BYTES = 10 * 1024 * 1024
DATASET_REPOSITORY = "SupingSun/ReproBoundary-Execution-Trajectories"
DATASET_REVISION = "57e17e11f795c6df9f7806ad2262fd32897ec2e6"
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

errors = []
tasks = list(csv.DictReader((ROOT / "task_pool/TASK_INVENTORY_47.csv").open(encoding="utf-8-sig")))
runs = list(csv.DictReader((ROOT / "trajectories/TRAJECTORY_INDEX.csv").open()))
evaluators = list(csv.DictReader((ROOT / "evaluators/EVALUATOR_INDEX.csv").open()))
if len(tasks) != 47 or len({row["project_id"] for row in tasks}) != 47:
    errors.append("task inventory is not 47 unique projects")
if len(evaluators) != 47 or len({row["project_id"] for row in evaluators}) != 47:
    errors.append("evaluator index is not 47 unique projects")
if len(runs) != 423 or len({row["task_id"] for row in runs}) != 423:
    errors.append("trajectory index is not 423 unique assignments")
if len({(row["base_model"], row["agent"]) for row in runs}) != 9:
    errors.append("trajectory index is not nine unique model-agent settings")
if {row["project"] for row in runs} != {row["project_id"] for row in tasks}:
    errors.append("trajectory projects do not match the task inventory")

for row in runs:
    relative = Path(row["trajectory_path"])
    if relative.parts[:2] != ("trajectories", "runs"):
        errors.append(f"unexpected external trajectory path for {row['task_id']}")
    if relative.name != "agent.log.gz":
        errors.append(f"unexpected trajectory filename for {row['task_id']}")
    if not SHA256_PATTERN.fullmatch(row["released_log_sha256"]):
        errors.append(f"invalid released hash for {row['task_id']}")

bundled_logs = list(ROOT.rglob("*.gz"))
if bundled_logs:
    for path in bundled_logs[:10]:
        errors.append(f"trajectory log must be hosted externally: {path.relative_to(ROOT)}")

manifest = json.loads((ROOT / "RELEASE_MANIFEST.json").read_text())
if manifest.get("trajectory_index_count") != 423:
    errors.append("manifest trajectory index count is not 423")
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
    if relative.startswith("trajectories/runs/"):
        errors.append(f"checksum includes external trajectory: {relative}")
        continue
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
    f"trajectory_records={len(runs)} bundled_logs={len(bundled_logs)}"
)
