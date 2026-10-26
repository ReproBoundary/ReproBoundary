#!/usr/bin/env python3
from __future__ import annotations

import csv
import gzip
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_EVALUATOR_FILE_BYTES = 1024 * 1024
MAX_EVALUATOR_BUNDLE_BYTES = 10 * 1024 * 1024

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

strong_patterns = {
    "local_path": re.compile(r"/Users/ssp|/lustre/prod_glm_volumes"),
    "api_key": re.compile(r"(?<![A-Za-z0-9])sk-(?:ant-)?[A-Za-z0-9_-]{12,}"),
    "service_token": re.compile(r"(?<![A-Za-z0-9])(?:ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|glpat-[A-Za-z0-9_-]{20,}|hf_[A-Za-z0-9]{30,})"),
    "authorization": re.compile(r"(?i)authorization\s*[:=]\s*(?:bearer|basic)\s+(?!<REDACTED>)[A-Za-z0-9][A-Za-z0-9._~+/-]{7,}"),
    "private_key": re.compile(r"BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY"),
}
for row in runs:
    log = ROOT / row["trajectory_path"]
    if not log.is_file():
        errors.append(f"missing released log for {row['task_id']}")
        continue
    if log.name != "agent.log.gz":
        errors.append(f"unexpected trajectory filename for {row['task_id']}")
    if sha256(log) != row["released_log_sha256"]:
        errors.append(f"released hash mismatch for {row['task_id']}")
    with gzip.open(log, "rt", encoding="utf-8", errors="replace") as handle:
        for line_number, line in enumerate(handle, 1):
            for name, pattern in strong_patterns.items():
                if pattern.search(line):
                    errors.append(f"residual {name}: {row['task_id']}:{line_number}")
                    break
            if errors and errors[-1].startswith("residual"):
                break

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
print(f"verification OK: tasks={len(tasks)} evaluators={len(evaluators)} trajectories={len(runs)}")
