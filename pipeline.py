#!/usr/bin/env python3
"""Export and run the public ReproBoundary task pipeline.

The runner intentionally contains no model- or framework-specific SDK. It
materializes the frozen public contracts, pins the upstream source revision,
passes the task prompt to a user-supplied coding-agent command, and launches
the exact evaluator command recorded in EVALUATOR_INDEX.csv.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime, timezone
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parent
TASKS_CSV = ROOT / "tasks" / "TASK_INVENTORY_47.csv"
EVALUATORS_CSV = ROOT / "evaluators" / "EVALUATOR_INDEX.csv"
TASK_EVALUATORS = ROOT / "evaluators" / "tasks"
PROMPT_TEMPLATE = ROOT / "AGENT_PROMPT.txt"
DELIVERABLE_FILES = (
    "DATASET_SELECTION.json",
    "pipeline-execution.json",
    "reproduction-report.md",
    "audit.json",
    "metrics.json",
    "security-attestation.json",
)
JSON_DELIVERABLE_FILES = tuple(name for name in DELIVERABLE_FILES if name.endswith(".json"))
SUBMISSION_LABEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def as_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized not in {"true", "false"}:
        raise ValueError(f"expected True or False, got {value!r}")
    return normalized == "true"


def load_catalog() -> tuple[list[dict[str, str]], dict[str, dict[str, str]]]:
    tasks = read_csv(TASKS_CSV)
    evaluators = read_csv(EVALUATORS_CSV)
    task_ids = [row["project_id"] for row in tasks]
    evaluator_ids = [row["project_id"] for row in evaluators]
    if len(tasks) != 47 or len(set(task_ids)) != 47:
        raise RuntimeError("task catalog must contain 47 unique project IDs")
    if len(evaluators) != 47 or len(set(evaluator_ids)) != 47:
        raise RuntimeError("evaluator catalog must contain 47 unique project IDs")
    if set(task_ids) != set(evaluator_ids):
        raise RuntimeError("task and evaluator project IDs do not match")
    return tasks, {row["project_id"]: row for row in evaluators}


def load_project(project_id: str) -> tuple[dict[str, str], dict[str, str], dict[str, Any], Path]:
    tasks, evaluators = load_catalog()
    task = next((row for row in tasks if row["project_id"] == project_id), None)
    if task is None:
        raise RuntimeError(f"unknown project ID: {project_id}")
    evaluator = evaluators[project_id]
    contract_path = TASK_EVALUATORS / project_id / "TARGET_EVALUATION.json"
    if not contract_path.is_file():
        raise RuntimeError(f"missing contract: {contract_path.relative_to(ROOT)}")
    actual_hash = sha256(contract_path)
    expected_hashes = {task["target_contract_sha256"], evaluator["contract_sha256"]}
    if expected_hashes != {actual_hash}:
        raise RuntimeError(f"contract hash mismatch for {project_id}")
    with contract_path.open(encoding="utf-8") as stream:
        contract = json.load(stream)
    if contract.get("project_id") != project_id:
        raise RuntimeError(f"contract project ID mismatch for {project_id}")
    return task, evaluator, contract, contract_path


def evaluator_record(row: dict[str, str]) -> dict[str, Any]:
    command = json.loads(row["evaluator_command_json"])
    if not isinstance(command, list) or not command or not all(isinstance(item, str) for item in command):
        raise RuntimeError(f"invalid evaluator command for {row['project_id']}")
    return {
        "name": row["evaluator_name"],
        "source_url": row["evaluator_source_url"],
        "version": row["evaluator_version"],
        "command": command,
        "deterministic": as_bool(row["deterministic"]),
        "requires_secret": as_bool(row["requires_secret"]),
        "requires_paid_api": as_bool(row["requires_paid_api"]),
        "contract_sha256": row["contract_sha256"],
        "bundled_helper_files": [item for item in row["bundled_helper_files"].split(";") if item],
    }


def json_dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")
    temporary.replace(path)


def text_dump(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(content)


def canonical_run_dir(path: Path, *, create: bool = False) -> Path:
    if path.is_symlink():
        raise RuntimeError(f"run directory must not be a symlink: {path}")
    if create:
        path.mkdir(parents=True, exist_ok=True)
    try:
        resolved = path.resolve(strict=True)
    except FileNotFoundError as error:
        raise RuntimeError(f"run directory does not exist: {path}") from error
    if not resolved.is_dir():
        raise RuntimeError(f"run directory is not a directory: {resolved}")
    return resolved


def contained_path(root: Path, relative: str | Path, *, must_exist: bool = False) -> Path:
    relative_path = Path(relative)
    if relative_path.is_absolute() or not relative_path.parts or ".." in relative_path.parts:
        raise RuntimeError(f"unsafe path below {root}: {relative_path}")
    root = root.resolve(strict=True)
    current = root
    for part in relative_path.parts:
        current = current / part
        if current.is_symlink():
            raise RuntimeError(f"symlink is not allowed in run paths: {current}")
    try:
        resolved = current.resolve(strict=must_exist)
    except FileNotFoundError as error:
        raise RuntimeError(f"required run path is missing: {current}") from error
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise RuntimeError(f"path escapes its run directory: {current}") from error
    return resolved


def select_project_ids(requested: list[str], tasks: Iterable[dict[str, str]]) -> list[str]:
    available = [row["project_id"] for row in tasks]
    if not requested:
        return available
    unknown = sorted(set(requested) - set(available))
    if unknown:
        raise RuntimeError(f"unknown project IDs: {', '.join(unknown)}")
    requested_set = set(requested)
    return [project_id for project_id in available if project_id in requested_set]


def export_dataset(args: argparse.Namespace) -> int:
    tasks, evaluators = load_catalog()
    project_ids = select_project_ids(args.project_id, tasks)
    output_dir = args.output.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    dataset_path = output_dir / "tasks.jsonl"
    with dataset_path.open("w", encoding="utf-8", newline="\n") as stream:
        for project_id in project_ids:
            task, evaluator, contract, contract_path = load_project(project_id)
            record = {
                "schema_version": "1.0",
                "project_id": project_id,
                "task": task,
                "contract": contract,
                "contract_path": str(contract_path.relative_to(ROOT)),
                "evaluator": evaluator_record(evaluator),
            }
            stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    manifest = {
        "schema_version": "1.0",
        "dataset": "ReproBoundary frozen task contracts",
        "task_count": len(project_ids),
        "project_ids": project_ids,
        "tasks_jsonl": dataset_path.name,
        "tasks_jsonl_sha256": sha256(dataset_path),
        "source_files": {
            str(TASKS_CSV.relative_to(ROOT)): sha256(TASKS_CSV),
            str(EVALUATORS_CSV.relative_to(ROOT)): sha256(EVALUATORS_CSV),
        },
    }
    json_dump(output_dir / "manifest.json", manifest)
    print(
        f"exported dataset: tasks={len(project_ids)} "
        f"path={dataset_path} sha256={manifest['tasks_jsonl_sha256']}"
    )
    return 0


def ensure_new_directory(path: Path) -> None:
    if path.is_symlink():
        raise RuntimeError(f"run directory must not be a symlink: {path}")
    if path.exists() and any(path.iterdir()):
        raise RuntimeError(f"refusing to overwrite non-empty run directory: {path}")
    path.mkdir(parents=True, exist_ok=True)


def run_checked(command: list[str], *, cwd: Path | None = None) -> None:
    rendered = shlex.join(command)
    print(f"+ {rendered}")
    subprocess.run(command, cwd=cwd, check=True)


def clone_source(task: dict[str, str], workspace: Path) -> None:
    workspace.parent.mkdir(parents=True, exist_ok=True)
    run_checked(
        [
            "git",
            "clone",
            "--filter=blob:none",
            "--no-checkout",
            task["repository_url"],
            str(workspace),
        ]
    )
    run_checked(["git", "checkout", "--detach", task["repository_commit"]], cwd=workspace)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=workspace, text=True).strip()
    if head != task["repository_commit"]:
        raise RuntimeError(f"source checkout mismatch: expected {task['repository_commit']}, got {head}")


def copy_helpers(project_id: str, helper_files: list[str], input_dir: Path, workspace: Path) -> None:
    source_root = TASK_EVALUATORS / project_id
    for relative in helper_files:
        relative_path = Path(relative)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise RuntimeError(f"unsafe evaluator helper path: {relative}")
        source = source_root / relative_path
        if not source.is_file():
            raise RuntimeError(f"missing evaluator helper: {source.relative_to(ROOT)}")
        for root in (input_dir / "evaluator", workspace):
            root.mkdir(parents=True, exist_ok=True)
            destination = contained_path(root, relative_path)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)


def verify_workspace_helpers(project_id: str, helper_files: list[str], workspace: Path) -> None:
    source_root = TASK_EVALUATORS / project_id
    for relative in helper_files:
        relative_path = Path(relative)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise RuntimeError(f"unsafe evaluator helper path: {relative}")
        canonical = source_root / relative_path
        workspace_copy = contained_path(workspace, relative_path, must_exist=True)
        if not workspace_copy.is_file():
            raise RuntimeError(f"workspace evaluator helper is not a file: {relative}")
        if sha256(workspace_copy) != sha256(canonical):
            raise RuntimeError(f"workspace evaluator helper hash mismatch: {relative}")


def paper_context(task: dict[str, str]) -> str:
    return "\n".join(
        [
            f"# {task['paper_title']}",
            "",
            f"- Project ID: `{task['project_id']}`",
            f"- Source repository: {task['repository_url']}",
            f"- Frozen commit: `{task['repository_commit']}`",
            f"- Target experiment: {task['target_task']}",
            f"- Target metric: {task['target_metric']} ({task['metric_direction']})",
            f"- Evaluation data: {task['evaluation_dataset']}, {task['evaluation_split']}",
            "",
            "Read the supplied paper and TARGET_EVALUATION contract for the complete method, data, budget, and evidence requirements.",
            "",
        ]
    )


def render_prompt(project_id: str, contract: dict[str, Any], run_dir: Path, workspace: Path) -> str:
    experiment_seconds = experiment_timeout_seconds(contract)
    prompt = PROMPT_TEMPLATE.read_text(encoding="utf-8")
    official_timeout_text = (
        "Experimentation may continue for <EXPERIMENT_MINUTES> minutes. At minute "
        "<EXPERIMENT_MINUTES>, the host will terminate this experiment session and its process tree. "
        "Stop all setup, downloads, pipeline stages, task-model inference, prediction generation, and "
        "evaluation by that deadline. A separate evidence-only session may use minutes "
        "<EXPERIMENT_MINUTES>-<HARD_LIMIT_MINUTES> solely to finalize deliverables from already completed "
        "work. Do not start or resume a pipeline stage during finalization. The container is forcibly "
        "terminated at minute <HARD_LIMIT_MINUTES>."
    )
    public_timeout_text = (
        f"This public helper permits at most {experiment_seconds} seconds for its single agent process "
        "and terminates that process tree at the limit. It does not start the separate evidence-only "
        "finalization session used by the official benchmark harness. Finish and checkpoint all required "
        "deliverables within this one process; do not assume that a later finalization session will run."
    )
    if official_timeout_text not in prompt:
        raise RuntimeError("agent prompt timeout paragraph no longer matches the public renderer")
    prompt = prompt.replace(official_timeout_text, public_timeout_text)
    replacements = {
        "<PROJECT_ID>": project_id,
        "/input/task-config.json": str((run_dir / "input" / "task-config.json").resolve()),
        "/workspace/task": str(workspace.resolve()),
    }
    for old, new in replacements.items():
        prompt = prompt.replace(old, new)
    if "<EXPERIMENT_MINUTES>" in prompt or "<HARD_LIMIT_MINUTES>" in prompt:
        raise RuntimeError("unresolved timeout placeholder in rendered prompt")
    return prompt


def prepare_run(args: argparse.Namespace) -> int:
    task, evaluator_row, contract, contract_path = load_project(args.project_id)
    evaluator = evaluator_record(evaluator_row)
    ensure_new_directory(args.output)
    run_dir = canonical_run_dir(args.output)
    input_dir = contained_path(run_dir, "input")
    workspace_parent = contained_path(run_dir, "workspace")
    workspace = contained_path(run_dir, "workspace/task")
    input_dir.mkdir(parents=True)
    workspace_parent.mkdir(parents=True, exist_ok=True)
    if args.clone_source:
        clone_source(task, workspace)
    else:
        workspace.mkdir(parents=True)

    task_config_path = contained_path(run_dir, "input/task-config.json")
    shutil.copy2(contract_path, task_config_path)
    copy_helpers(args.project_id, evaluator["bundled_helper_files"], input_dir, workspace)
    json_dump(contained_path(workspace, "PROJECT_TASK.json"), task)
    text_dump(contained_path(workspace, "PAPER_CONTEXT.md"), paper_context(task))
    if args.paper is not None:
        paper = args.paper.resolve()
        if not paper.is_file():
            raise RuntimeError(f"paper is not a readable PDF: {paper}")
        with paper.open("rb") as stream:
            if stream.read(5) != b"%PDF-":
                raise RuntimeError(f"paper is not a readable PDF: {paper}")
        shutil.copy2(paper, contained_path(workspace, "PAPER.pdf"))

    prompt_path = contained_path(run_dir, "prompt.txt")
    text_dump(prompt_path, render_prompt(args.project_id, contract, run_dir, workspace))
    manifest = {"schema_version": "1.1", "project_id": args.project_id}
    json_dump(contained_path(run_dir, "run.json"), manifest)
    print(f"prepared run: project_id={args.project_id} path={run_dir}")
    if not args.clone_source:
        print("source checkout not requested; populate workspace/task at the frozen commit before inference")
    if args.paper is None:
        print("paper not supplied; add the project paper as workspace/task/PAPER.pdf before inference")
    return 0


def load_run(
    requested_run_dir: Path,
) -> tuple[Path, dict[str, str], dict[str, Any], dict[str, Any], Path, Path, Path]:
    run_dir = canonical_run_dir(requested_run_dir)
    manifest_path = contained_path(run_dir, "run.json", must_exist=True)
    if not manifest_path.is_file():
        raise RuntimeError(f"run manifest is not a regular file: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise RuntimeError("run manifest must be a JSON object")
    project_id = manifest.get("project_id")
    if not isinstance(project_id, str) or not project_id:
        raise RuntimeError("run manifest must contain one valid project_id")

    task, evaluator_row, contract, canonical_contract = load_project(project_id)
    evaluator = evaluator_record(evaluator_row)
    workspace = contained_path(run_dir, "workspace/task", must_exist=True)
    task_config = contained_path(run_dir, "input/task-config.json", must_exist=True)
    prompt = contained_path(run_dir, "prompt.txt", must_exist=True)
    if not workspace.is_dir() or not task_config.is_file() or not prompt.is_file():
        raise RuntimeError("run directory is incomplete; rerun prepare-run")
    if sha256(task_config) != sha256(canonical_contract):
        raise RuntimeError("run task contract differs from the canonical release contract")
    expected_prompt = render_prompt(project_id, contract, run_dir, workspace)
    if prompt.read_text(encoding="utf-8") != expected_prompt:
        raise RuntimeError("run prompt differs from the canonical rendered prompt")

    git_marker = workspace / ".git"
    if git_marker.is_symlink():
        raise RuntimeError("workspace Git metadata must not be a symlink")
    if git_marker.exists():
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=workspace, text=True).strip()
        if head != task["repository_commit"]:
            raise RuntimeError(
                f"workspace commit mismatch: expected {task['repository_commit']}, got {head}"
            )
    return run_dir, task, evaluator, contract, workspace, task_config, prompt


def experiment_timeout_seconds(contract: dict[str, Any]) -> int:
    value = contract.get("timeout_policy", {}).get("experiment_seconds")
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise RuntimeError("contract experiment_seconds must be a positive integer")
    return value


def bounded_timeout(requested: int | None, contract: dict[str, Any]) -> int:
    maximum = experiment_timeout_seconds(contract)
    if requested is None:
        return maximum
    if requested <= 0:
        raise RuntimeError("timeout-seconds must be positive")
    if requested > maximum:
        raise RuntimeError(f"timeout-seconds exceeds the contract experiment limit of {maximum}")
    return requested


def expand_command(command: list[str], values: dict[str, str]) -> list[str]:
    expanded = []
    for argument in command:
        for marker, value in values.items():
            argument = argument.replace("{" + marker + "}", value)
        expanded.append(argument)
    return expanded


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def execute_logged(
    command: list[str],
    *,
    cwd: Path,
    log_path: Path,
    metadata_path: Path,
    timeout_seconds: int,
    stdin_text: str | None,
    env: dict[str, str],
    dry_run: bool,
) -> int:
    print(f"cwd: {cwd}")
    print(f"command: {shlex.join(command)}")
    if dry_run:
        print("dry-run: command not executed")
        return 0
    log_path.parent.mkdir(parents=True, exist_ok=True)
    started = utc_now()
    metadata = {
        "command": command,
        "cwd": str(cwd),
        "started_at": started,
        "finished_at": None,
        "exit_code": None,
        "timed_out": False,
        "timeout_seconds": timeout_seconds,
        "log": str(log_path),
    }
    json_dump(metadata_path, metadata)
    with log_path.open("w", encoding="utf-8", newline="\n") as log:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            env=env,
            stdin=subprocess.PIPE if stdin_text is not None else subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )
        try:
            process.communicate(input=stdin_text, timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            metadata["timed_out"] = True
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
    metadata["finished_at"] = utc_now()
    metadata["exit_code"] = process.returncode
    json_dump(metadata_path, metadata)
    print(f"exit_code={process.returncode} log={log_path}")
    return int(process.returncode)


def runtime_environment(
    run_dir: Path, project_id: str, workspace: Path, task_config: Path, prompt: Path
) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "REPROBOUNDARY_RUN_DIR": str(run_dir),
            "REPROBOUNDARY_PROJECT_ID": project_id,
            "REPROBOUNDARY_WORKSPACE": str(workspace),
            "REPROBOUNDARY_TASK_CONFIG": str(task_config),
            "REPROBOUNDARY_PROMPT": str(prompt),
        }
    )
    return env


def infer(args: argparse.Namespace) -> int:
    run_dir, task, evaluator, contract, workspace, task_config, prompt = load_run(args.run_dir)
    command = list(args.agent_command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        raise RuntimeError("provide an agent command after --")
    if not args.dry_run and not (workspace / ".git").is_dir():
        raise RuntimeError("workspace has no pinned Git checkout; rerun prepare-run with --clone-source")
    verify_workspace_helpers(task["project_id"], evaluator["bundled_helper_files"], workspace)
    values = {
        "run_dir": str(run_dir),
        "workspace": str(workspace),
        "task_config": str(task_config),
        "prompt": str(prompt),
        "project_id": task["project_id"],
    }
    command = expand_command(command, values)
    timeout = bounded_timeout(args.timeout_seconds, contract)
    stdin_text = None if args.no_prompt_stdin else prompt.read_text(encoding="utf-8")
    log_path = contained_path(run_dir, "logs/agent.log")
    metadata_path = contained_path(run_dir, "logs/agent-command.json")
    return execute_logged(
        command,
        cwd=workspace,
        log_path=log_path,
        metadata_path=metadata_path,
        timeout_seconds=timeout,
        stdin_text=stdin_text,
        env=runtime_environment(run_dir, task["project_id"], workspace, task_config, prompt),
        dry_run=args.dry_run,
    )


def evaluate(args: argparse.Namespace) -> int:
    run_dir, task, evaluator, contract, workspace, task_config, prompt = load_run(args.run_dir)
    command = evaluator["command"]
    if not isinstance(command, list) or not command:
        raise RuntimeError("canonical evaluator index has no evaluator command")
    if not args.dry_run and not (workspace / ".git").is_dir():
        raise RuntimeError("workspace has no pinned Git checkout; rerun prepare-run with --clone-source")
    verify_workspace_helpers(task["project_id"], evaluator["bundled_helper_files"], workspace)
    timeout = bounded_timeout(args.timeout_seconds, contract)
    log_path = contained_path(run_dir, "logs/evaluator.log")
    metadata_path = contained_path(run_dir, "logs/evaluator-command.json")
    return execute_logged(
        command,
        cwd=workspace,
        log_path=log_path,
        metadata_path=metadata_path,
        timeout_seconds=timeout,
        stdin_text=None,
        env=runtime_environment(run_dir, task["project_id"], workspace, task_config, prompt),
        dry_run=args.dry_run,
    )


def safe_submission_label(value: str, field: str) -> str:
    if not SUBMISSION_LABEL.fullmatch(value):
        raise RuntimeError(
            f"{field} must use 1-80 ASCII letters, digits, '.', '_' or '-' and start with a letter or digit"
        )
    return value


def safe_relative_submission_path(raw: str) -> PurePosixPath:
    if not isinstance(raw, str) or not raw or "\\" in raw:
        raise RuntimeError(f"invalid relative artifact path: {raw!r}")
    path = PurePosixPath(raw)
    if (
        path.is_absolute()
        or raw.rstrip("/") != str(path)
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise RuntimeError(f"unsafe relative artifact path: {raw!r}")
    return path


def require_fields(payload: dict[str, Any], fields: Iterable[str], filename: str) -> None:
    missing = [field for field in fields if field not in payload]
    if missing:
        raise RuntimeError(f"{filename} is missing required fields: {', '.join(missing)}")


def load_submission_deliverables(results_dir: Path) -> dict[str, Any]:
    deliverables: dict[str, Any] = {}
    for filename in DELIVERABLE_FILES:
        path = contained_path(results_dir, filename, must_exist=True)
        if not path.is_file():
            raise RuntimeError(f"required deliverable is not a regular file: {filename}")
        if filename.endswith(".json"):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise RuntimeError(f"invalid JSON deliverable {filename}: {error}") from error
            if not isinstance(payload, dict):
                raise RuntimeError(f"{filename} must contain one JSON object")
            deliverables[filename] = payload
        else:
            try:
                report = path.read_text(encoding="utf-8")
            except UnicodeDecodeError as error:
                raise RuntimeError(f"{filename} must be UTF-8 text") from error
            if not report.strip():
                raise RuntimeError(f"{filename} must not be empty")
            deliverables[filename] = report
    return deliverables


def validate_contract_deliverables(
    project_id: str,
    contract: dict[str, Any],
    contract_hash: str,
    deliverables: dict[str, Any],
) -> None:
    required_output = contract.get("required_agent_output", {})
    required_files = required_output.get("required_files")
    if required_files != list(DELIVERABLE_FILES):
        raise RuntimeError("the released contract does not use the supported six-file v4 output set")
    if set(deliverables) != set(DELIVERABLE_FILES):
        raise RuntimeError("submission deliverables do not match the contract-required file set")
    if not isinstance(deliverables["reproduction-report.md"], str) or not deliverables[
        "reproduction-report.md"
    ].strip():
        raise RuntimeError("reproduction-report.md must be non-empty UTF-8 text")

    schema_version = required_output.get("schema_version")
    field_groups = {
        "DATASET_SELECTION.json": "dataset_selection_required_fields",
        "pipeline-execution.json": "pipeline_execution_required_fields",
        "metrics.json": "metrics_required_fields",
        "security-attestation.json": "security_attestation_required_fields",
    }
    legacy_security_fields = [
        "schema_version",
        "project_id",
        "target_contract_sha256",
        "security_policy_id",
        "security_policy_sha256",
        "declared_events",
        "no_undeclared_security_events",
        "notes",
    ]
    for filename in JSON_DELIVERABLE_FILES:
        payload = deliverables[filename]
        if not isinstance(payload, dict):
            raise RuntimeError(f"{filename} must contain one JSON object")
        require_fields(payload, ("schema_version", "project_id", "target_contract_sha256"), filename)
        if payload["schema_version"] != schema_version:
            raise RuntimeError(f"{filename} schema_version does not match the task contract")
        if payload["project_id"] != project_id:
            raise RuntimeError(f"{filename} project_id does not match the submission")
        if payload["target_contract_sha256"] != contract_hash:
            raise RuntimeError(f"{filename} target_contract_sha256 does not match the released contract")
        field_group = field_groups.get(filename)
        if field_group:
            fields = required_output.get(field_group)
            if fields is None and filename == "security-attestation.json":
                fields = legacy_security_fields
            if not isinstance(fields, list) or not all(isinstance(field, str) for field in fields):
                raise RuntimeError(f"contract field list is invalid: {field_group}")
            require_fields(payload, fields, filename)

    dataset = deliverables["DATASET_SELECTION.json"]
    reduced = contract.get("reduced_reproduction", {})
    templates = required_output.get("output_templates") or {}
    expected_dataset = templates.get("DATASET_SELECTION.json", {})
    expected_execution = templates.get("pipeline-execution.json", {})
    expected_protocol_id = expected_dataset.get("reduction_protocol_id", reduced.get("protocol_id"))
    expected_data_scopes = expected_dataset.get("data_scopes", reduced.get("data_scopes"))
    expected_stage_budgets = expected_dataset.get("stage_budgets", reduced.get("stage_budgets"))
    if dataset.get("target_metric_id") != contract.get("target_metric_id"):
        raise RuntimeError("DATASET_SELECTION.json target_metric_id does not match the contract")
    if dataset.get("reduction_protocol_id") != expected_protocol_id:
        raise RuntimeError("DATASET_SELECTION.json reduction_protocol_id does not match the contract")
    if dataset.get("data_scopes") != expected_data_scopes:
        raise RuntimeError("DATASET_SELECTION.json data_scopes differ from the frozen contract")
    if dataset.get("stage_budgets") != expected_stage_budgets:
        raise RuntimeError("DATASET_SELECTION.json stage_budgets differ from the frozen contract")
    if dataset.get("no_unplanned_reductions") is not True:
        raise RuntimeError("DATASET_SELECTION.json must set no_unplanned_reductions to true")

    execution = deliverables["pipeline-execution.json"]
    if execution.get("reduction_protocol_id") != expected_execution.get(
        "reduction_protocol_id", reduced.get("protocol_id")
    ):
        raise RuntimeError("pipeline-execution.json reduction_protocol_id does not match the contract")
    if execution.get("actual_data_scopes") != expected_execution.get(
        "actual_data_scopes", reduced.get("data_scopes")
    ):
        raise RuntimeError("pipeline-execution.json actual_data_scopes differ from the frozen contract")
    if execution.get("actual_stage_budgets") != expected_execution.get(
        "actual_stage_budgets", reduced.get("stage_budgets")
    ):
        raise RuntimeError("pipeline-execution.json actual_stage_budgets differ from the frozen contract")
    if execution.get("pipeline_status") not in required_output.get("pipeline_status_values", []):
        raise RuntimeError("pipeline-execution.json has an invalid pipeline_status")
    if not isinstance(execution.get("deviations"), list):
        raise RuntimeError("pipeline-execution.json deviations must be an array")
    stages = execution.get("stages")
    if not isinstance(stages, list):
        raise RuntimeError("pipeline-execution.json stages must be an array")
    if isinstance(expected_execution.get("stages"), list):
        expected_stage_ids = [stage.get("stage_id") for stage in expected_execution["stages"]]
    else:
        expected_stage_ids = [
            stage.get("stage_id")
            for stage in reduced.get("pipeline_stages", [])
            if isinstance(stage, dict) and stage.get("must_execute") is True
        ]
    actual_stage_ids = [stage.get("stage_id") for stage in stages if isinstance(stage, dict)]
    if actual_stage_ids != expected_stage_ids or len(actual_stage_ids) != len(stages):
        raise RuntimeError("pipeline-execution.json stages do not match the required pipeline stages")
    stage_fields = required_output.get("pipeline_stage_record_fields", [])
    stage_statuses = required_output.get("pipeline_stage_status_values", [])
    for stage in stages:
        require_fields(stage, stage_fields, "pipeline-execution.json stage")
        if stage.get("status") not in stage_statuses:
            raise RuntimeError(f"invalid status for pipeline stage {stage.get('stage_id')}")
        for field in ("commands", "exit_codes", "input_artifacts", "output_artifacts", "evidence_paths"):
            if not isinstance(stage.get(field), list):
                raise RuntimeError(f"pipeline stage {stage.get('stage_id')} field {field} must be an array")
        for field in ("input_artifacts", "output_artifacts", "evidence_paths"):
            for relative in stage[field]:
                if not isinstance(relative, str) or not relative:
                    raise RuntimeError(
                        f"pipeline stage {stage.get('stage_id')} field {field} contains an invalid path"
                    )
                safe_relative_submission_path(relative)
        if len(stage["commands"]) != len(stage["exit_codes"]):
            raise RuntimeError(f"pipeline stage {stage.get('stage_id')} command and exit-code counts differ")
        if stage.get("status") != "not_started":
            if not stage["commands"] or not all(isinstance(code, int) for code in stage["exit_codes"]):
                raise RuntimeError(f"started pipeline stage {stage.get('stage_id')} lacks commands or exit codes")
            if not str(stage.get("started_at", "")).strip() or not str(stage.get("finished_at", "")).strip():
                raise RuntimeError(f"started pipeline stage {stage.get('stage_id')} lacks timestamps")
    if execution.get("pipeline_status") == "pipeline_complete":
        if any(stage.get("status") != "completed" for stage in stages) or execution["deviations"]:
            raise RuntimeError("pipeline_complete requires every stage completed with no deviations")

    audit = deliverables["audit.json"]
    if "audit.json" in templates:
        require_fields(audit, templates["audit.json"].keys(), "audit.json")
        if not isinstance(audit.get("events"), list) or not isinstance(audit.get("notes"), str):
            raise RuntimeError("audit.json must contain an events array and notes string")

    metrics = deliverables["metrics.json"]
    if metrics.get("target_metric_id") != contract.get("target_metric_id"):
        raise RuntimeError("metrics.json target_metric_id does not match the contract")
    if metrics.get("pipeline_status") != execution.get("pipeline_status"):
        raise RuntimeError("metrics.json and pipeline-execution.json disagree on pipeline_status")
    if metrics.get("reproduction_status") not in required_output.get("reproduction_status_values", []):
        raise RuntimeError("metrics.json has an invalid reproduction_status")
    if metrics.get("comparability_status") not in required_output.get("comparability_status_values", []):
        raise RuntimeError("metrics.json has an invalid comparability_status")
    for field in ("metrics", "auxiliary_metrics", "target_protocol_deviations"):
        if not isinstance(metrics.get(field), list):
            raise RuntimeError(f"metrics.json field {field} must be an array")
    obtained = metrics.get("target_metric_obtained")
    if not isinstance(obtained, bool):
        raise RuntimeError("metrics.json target_metric_obtained must be a boolean")
    if obtained and not metrics["metrics"]:
        raise RuntimeError("metrics.json claims a target metric but contains no primary metric entry")
    if not obtained and (metrics["metrics"] or not str(metrics.get("no_metric_reason", "")).strip()):
        raise RuntimeError("a no-metric submission must have no primary metric and a non-empty no_metric_reason")
    if obtained:
        if len(metrics["metrics"]) != 1:
            raise RuntimeError("metrics.json must contain exactly one primary target metric")
        primary = metrics["metrics"][0]
        if not isinstance(primary, dict):
            raise RuntimeError("metrics.json primary metric entry must be an object")
        require_fields(primary, required_output.get("primary_metric_entry_fields", []), "metrics.json metric")
        if primary.get("metric_id") != contract.get("target_metric_id"):
            raise RuntimeError("metrics.json primary metric_id does not match the contract")
    if metrics.get("reproduction_status") == "completed_reproduction" and not (
        obtained
        and metrics.get("comparability_status") == "comparable"
        and metrics.get("pipeline_status") == "pipeline_complete"
        and not metrics["target_protocol_deviations"]
    ):
        raise RuntimeError("completed_reproduction requires a comparable metric and complete, undeviated pipeline")

    security = deliverables["security-attestation.json"]
    policy = contract.get("security_policy", {})
    if security.get("security_policy_id") != policy.get("policy_id"):
        raise RuntimeError("security-attestation.json security_policy_id does not match the contract")
    if security.get("security_policy_sha256") != policy.get("source_sha256"):
        raise RuntimeError("security-attestation.json security_policy_sha256 does not match the contract")
    if not isinstance(security.get("declared_events"), list):
        raise RuntimeError("security-attestation.json declared_events must be an array")
    if not isinstance(security.get("no_undeclared_security_events"), bool):
        raise RuntimeError("security-attestation.json no_undeclared_security_events must be a boolean")
    if not isinstance(security.get("notes"), str):
        raise RuntimeError("security-attestation.json notes must be a string")


def collect_artifact_references(deliverables: dict[str, Any]) -> list[str]:
    scalar_keys = {"evidence_path", "selected_ids_path"}
    array_keys = {"evidence_paths", "output_artifacts"}
    references: set[str] = set()

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key in scalar_keys and child is not None:
                    if not isinstance(child, str) or not child:
                        raise RuntimeError(f"{key} must be a non-empty relative path or null")
                    references.add(str(safe_relative_submission_path(child)))
                elif key in array_keys:
                    if not isinstance(child, list):
                        raise RuntimeError(f"{key} must be an array of relative paths")
                    for item in child:
                        if not isinstance(item, str) or not item:
                            raise RuntimeError(f"{key} contains an invalid path")
                        references.add(str(safe_relative_submission_path(item)))
                else:
                    visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    for payload in deliverables.values():
        visit(payload)
    return sorted(references)


def resolve_artifact_reference(workspace: Path, results_dir: Path, relative: str) -> Path:
    relative_path = Path(*PurePosixPath(relative).parts)
    candidates: list[Path] = []
    for root in (results_dir, workspace):
        try:
            candidate = contained_path(root, relative_path, must_exist=True)
        except RuntimeError:
            continue
        if candidate.exists() and candidate not in candidates:
            candidates.append(candidate)
    if not candidates:
        raise RuntimeError(f"referenced artifact is missing: {relative}")
    if len(candidates) > 1 and len({candidate.resolve() for candidate in candidates}) > 1:
        raise RuntimeError(f"referenced artifact is ambiguous between the workspace and results: {relative}")
    return candidates[0]


def copy_artifact(source: Path, destination: Path) -> None:
    if source.is_symlink():
        raise RuntimeError(f"artifact symlinks are not allowed: {source}")
    if source.is_file():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        return
    if not source.is_dir():
        raise RuntimeError(f"artifact is not a regular file or directory: {source}")
    for child in sorted(source.rglob("*")):
        if child.is_symlink():
            raise RuntimeError(f"artifact symlinks are not allowed: {child}")
        if child.is_file():
            target = destination / child.relative_to(source)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(child, target)
        elif not child.is_dir():
            raise RuntimeError(f"unsupported artifact file type: {child}")


def make_source_patch(workspace: Path, helper_files: list[str]) -> bytes:
    if not (workspace / ".git").is_dir():
        raise RuntimeError("cannot package source changes without a pinned Git checkout")
    exclusions = ["results", "PROJECT_TASK.json", "PAPER_CONTEXT.md", "PAPER.pdf", *helper_files]
    pathspec = [".", *[f":(exclude){relative}" for relative in exclusions]]
    tracked = subprocess.run(
        ["git", "diff", "--binary", "--no-ext-diff", "HEAD", "--", *pathspec],
        cwd=workspace,
        check=True,
        stdout=subprocess.PIPE,
    ).stdout
    untracked_raw = subprocess.check_output(
        ["git", "ls-files", "--others", "--exclude-standard", "-z"], cwd=workspace
    )
    excluded = {PurePosixPath(item) for item in exclusions}
    patch_parts = [tracked]
    for raw in untracked_raw.split(b"\0"):
        if not raw:
            continue
        relative = PurePosixPath(raw.decode("utf-8"))
        if relative.parts[0] == "results" or relative in excluded:
            continue
        source = contained_path(workspace, Path(*relative.parts), must_exist=True)
        if not source.is_file() or source.stat().st_size > 1024 * 1024:
            raise RuntimeError(f"untracked source must be a regular file no larger than 1 MiB: {relative}")
        diff = subprocess.run(
            ["git", "diff", "--no-index", "--binary", "--", "/dev/null", str(relative)],
            cwd=workspace,
            stdout=subprocess.PIPE,
        )
        if diff.returncode not in {0, 1}:
            raise RuntimeError(f"could not encode untracked source in source.patch: {relative}")
        patch_parts.append(diff.stdout)
    patch = b"".join(patch_parts)
    if len(patch) > 10 * 1024 * 1024:
        raise RuntimeError("source.patch exceeds 10 MiB; remove generated data from the source tree")
    return patch


def submission_claim(metrics: dict[str, Any]) -> str:
    if (
        metrics.get("target_metric_obtained") is True
        and metrics.get("reproduction_status") == "completed_reproduction"
        and metrics.get("comparability_status") == "comparable"
        and metrics.get("pipeline_status") == "pipeline_complete"
        and not metrics.get("target_protocol_deviations")
    ):
        return "complete_reproduction"
    if metrics.get("target_metric_obtained") is True:
        return "partial_result"
    return "no_metric"


def submission_file_records(root: Path) -> list[dict[str, Any]]:
    records = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise RuntimeError(f"submission symlinks are not allowed: {path.relative_to(root)}")
        if path.is_file() and path != root / "submission.json":
            records.append(
                {
                    "path": path.relative_to(root).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": sha256(path),
                }
            )
        elif not path.is_dir() and not path.is_file():
            raise RuntimeError(f"unsupported submission file type: {path.relative_to(root)}")
    return records


def validate_submission_directory(root: Path) -> tuple[str, int]:
    allowed_top_level = {"submission.json", "artifacts", "agent.log.gz", "source.patch"}
    actual_top_level = {path.name for path in root.iterdir()}
    required_top_level = {"submission.json", "artifacts", "agent.log.gz"}
    if not required_top_level.issubset(actual_top_level) or not actual_top_level.issubset(allowed_top_level):
        raise RuntimeError("submission must contain submission.json, artifacts/, agent.log.gz, and optional source.patch")
    if not (root / "artifacts").is_dir() or (root / "artifacts").is_symlink():
        raise RuntimeError("submission artifacts must be a real directory")
    submission_path = root / "submission.json"
    try:
        envelope = json.loads(submission_path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError(f"invalid submission.json: {error}") from error
    if not isinstance(envelope, dict) or envelope.get("schema_version") != "1.0":
        raise RuntimeError("submission.json must use submission schema 1.0")
    project_id = envelope.get("project_id")
    if not isinstance(project_id, str):
        raise RuntimeError("submission.json has no valid project_id")
    task, evaluator, contract, contract_path = load_project(project_id)
    contract_hash = sha256(contract_path)
    if envelope.get("benchmark") != "ReproBoundary":
        raise RuntimeError("submission.json benchmark must be ReproBoundary")
    if envelope.get("target_contract_sha256") != contract_hash:
        raise RuntimeError("submission.json target_contract_sha256 does not match the released contract")
    if envelope.get("source_commit") != task["repository_commit"]:
        raise RuntimeError("submission.json source_commit does not match the frozen task commit")
    for field in ("model", "agent"):
        value = envelope.get(field)
        if not isinstance(value, str):
            raise RuntimeError(f"submission.json has no valid {field}")
        safe_submission_label(value, field)
    expected_root_name = f"{project_id}-{envelope['model']}-{envelope['agent']}"
    if root.name != expected_root_name:
        raise RuntimeError(f"submission top-level directory must be {expected_root_name}")
    if envelope.get("artifact_root") != "artifacts":
        raise RuntimeError("submission.json artifact_root must be artifacts")
    deliverables = envelope.get("deliverables")
    if not isinstance(deliverables, dict):
        raise RuntimeError("submission.json deliverables must be an object")
    validate_contract_deliverables(project_id, contract, contract_hash, deliverables)
    if envelope.get("claim") != submission_claim(deliverables["metrics.json"]):
        raise RuntimeError("submission.json claim does not match metrics.json")

    expected_records = submission_file_records(root)
    records = envelope.get("files")
    if records != expected_records:
        raise RuntimeError("submission.json file manifest does not match the package files")
    for relative in collect_artifact_references(deliverables):
        artifact = root / "artifacts" / Path(*PurePosixPath(relative).parts)
        if not artifact.exists():
            raise RuntimeError(f"submission is missing referenced artifact: {relative}")
        try:
            artifact.resolve(strict=True).relative_to((root / "artifacts").resolve(strict=True))
        except ValueError as error:
            raise RuntimeError(f"artifact path escapes the package: {relative}") from error
    try:
        with gzip.open(root / "agent.log.gz", "rb") as stream:
            while stream.read(1024 * 1024):
                pass
    except (OSError, EOFError) as error:
        raise RuntimeError(f"agent.log.gz is not a valid gzip stream: {error}") from error
    return project_id, len(expected_records)


def pack_submission(args: argparse.Namespace) -> int:
    run_dir, task, evaluator, contract, workspace, task_config, _ = load_run(args.run_dir)
    model = safe_submission_label(args.model, "model")
    agent = safe_submission_label(args.agent, "agent")
    project_id = task["project_id"]
    expected_name = f"{project_id}-{model}-{agent}.tar.gz"
    output = args.output.resolve()
    if output.name != expected_name:
        raise RuntimeError(f"output filename must be {expected_name}")
    if output.exists():
        raise RuntimeError(f"refusing to overwrite existing submission: {output}")
    results_dir = contained_path(workspace, Path("results") / project_id, must_exist=True)
    if not results_dir.is_dir():
        raise RuntimeError(f"missing results directory: results/{project_id}")
    deliverables = load_submission_deliverables(results_dir)
    contract_hash = sha256(task_config)
    validate_contract_deliverables(project_id, contract, contract_hash, deliverables)
    agent_log = contained_path(run_dir, "logs/agent.log", must_exist=True)
    if not agent_log.is_file():
        raise RuntimeError("run has no regular logs/agent.log")

    output.parent.mkdir(parents=True, exist_ok=True)
    package_root_name = expected_name.removesuffix(".tar.gz")
    with tempfile.TemporaryDirectory(prefix="reproboundary-submit-") as temporary:
        root = Path(temporary) / package_root_name
        artifacts = root / "artifacts"
        artifacts.mkdir(parents=True)
        for relative in collect_artifact_references(deliverables):
            source = resolve_artifact_reference(workspace, results_dir, relative)
            copy_artifact(source, artifacts / Path(*PurePosixPath(relative).parts))
        evaluator_log = run_dir / "logs/evaluator.log"
        if evaluator_log.is_symlink():
            raise RuntimeError("evaluator log must not be a symlink")
        if evaluator_log.is_file():
            copy_artifact(evaluator_log, artifacts / "_run/evaluator.log")

        with agent_log.open("rb") as source, (root / "agent.log.gz").open("wb") as raw:
            with gzip.GzipFile(filename="agent.log", mode="wb", fileobj=raw, mtime=0) as compressed:
                shutil.copyfileobj(source, compressed)
        patch = make_source_patch(workspace, evaluator["bundled_helper_files"])
        if patch:
            (root / "source.patch").write_bytes(patch)
        envelope = {
            "schema_version": "1.0",
            "benchmark": "ReproBoundary",
            "project_id": project_id,
            "model": model,
            "agent": agent,
            "source_commit": task["repository_commit"],
            "target_contract_sha256": contract_hash,
            "claim": submission_claim(deliverables["metrics.json"]),
            "artifact_root": "artifacts",
            "deliverables": deliverables,
            "files": submission_file_records(root),
        }
        json_dump(root / "submission.json", envelope)
        validated_project, file_count = validate_submission_directory(root)
        if validated_project != project_id:
            raise RuntimeError("internal submission validation returned the wrong project")
        with tarfile.open(output, "w:gz", format=tarfile.PAX_FORMAT) as archive:
            archive.add(root, arcname=package_root_name, recursive=True)
    print(
        f"packed submission: project_id={project_id} files={file_count + 1} "
        f"path={output} sha256={sha256(output)}"
    )
    return 0


def validate_submission(args: argparse.Namespace) -> int:
    archive_path = args.archive.resolve()
    if not archive_path.is_file():
        raise RuntimeError(f"submission archive does not exist: {archive_path}")
    with tempfile.TemporaryDirectory(prefix="reproboundary-validate-") as temporary:
        destination = Path(temporary)
        with tarfile.open(archive_path, "r:gz") as archive:
            members = archive.getmembers()
            if not members:
                raise RuntimeError("submission archive is empty")
            seen: set[str] = set()
            roots: set[str] = set()
            for member in members:
                path = safe_relative_submission_path(member.name)
                if member.name.rstrip("/") != str(path):
                    raise RuntimeError(f"archive member path is not canonical: {member.name}")
                if member.name in seen:
                    raise RuntimeError(f"duplicate archive member: {member.name}")
                seen.add(member.name)
                roots.add(path.parts[0])
                if not (member.isfile() or member.isdir()):
                    raise RuntimeError(f"archive links and special files are not allowed: {member.name}")
            if len(roots) != 1:
                raise RuntimeError("submission archive must contain one top-level directory")
            archive.extractall(destination)
        root = destination / next(iter(roots))
        project_id, file_count = validate_submission_directory(root)
    print(
        f"submission OK: project_id={project_id} files={file_count + 1} "
        f"sha256={sha256(archive_path)}"
    )
    return 0


def show_task(args: argparse.Namespace) -> int:
    task, evaluator_row, contract, _ = load_project(args.project_id)
    print(f"{task['project_id']}: {task['paper_title']}")
    print(f"target: {task['target_task']}")
    print(f"metric: {task['target_metric']} ({task['metric_direction']})")
    print(f"source: {task['repository_url']} @ {task['repository_commit']}")
    print("pipeline:")
    stages = contract.get("reduced_reproduction", {}).get("pipeline_stages", [])
    for index, stage in enumerate(stages, 1):
        entrypoint = stage.get("official_entrypoint", [])
        print(f"  {index}. {stage.get('stage_id')}: {stage.get('name')}")
        if entrypoint:
            print(f"     {shlex.join(entrypoint)}")
    evaluator = evaluator_record(evaluator_row)
    print(f"evaluator: {shlex.join(evaluator['command'])}")
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)

    export = commands.add_parser("export-dataset", help="export JSONL records from the frozen public contracts")
    export.add_argument("--output", type=Path, default=Path("build/reproboundary"))
    export.add_argument("--project-id", action="append", default=[], help="include only this project; repeatable")
    export.set_defaults(handler=export_dataset)

    show = commands.add_parser("show", help="show one task's frozen stages and evaluator")
    show.add_argument("project_id")
    show.set_defaults(handler=show_task)

    prepare = commands.add_parser("prepare-run", help="materialize one frozen task run directory")
    prepare.add_argument("project_id")
    prepare.add_argument("--output", type=Path, required=True)
    prepare.add_argument("--paper", type=Path, help="local copy of the matching source-paper PDF")
    prepare.add_argument("--clone-source", action="store_true", help="clone and checkout the pinned upstream commit")
    prepare.set_defaults(handler=prepare_run)

    run = commands.add_parser("infer", help="pass the frozen prompt to a coding-agent command")
    run.add_argument("--run-dir", type=Path, required=True)
    run.add_argument("--timeout-seconds", type=int)
    run.add_argument("--no-prompt-stdin", action="store_true")
    run.add_argument("--dry-run", action="store_true")
    run.add_argument("agent_command", nargs=argparse.REMAINDER)
    run.set_defaults(handler=infer)

    score = commands.add_parser("evaluate", help="run the task's frozen evaluator command")
    score.add_argument("--run-dir", type=Path, required=True)
    score.add_argument("--timeout-seconds", type=int)
    score.add_argument("--dry-run", action="store_true")
    score.set_defaults(handler=evaluate)

    package = commands.add_parser(
        "pack-submission", help="validate one run and create the compact leaderboard package"
    )
    package.add_argument("--run-dir", type=Path, required=True)
    package.add_argument("--model", required=True, help="short model label used in the archive name")
    package.add_argument("--agent", required=True, help="short agent label used in the archive name")
    package.add_argument("--output", type=Path, required=True, help="exact <project>-<model>-<agent>.tar.gz path")
    package.set_defaults(handler=pack_submission)

    validate = commands.add_parser(
        "validate-submission", help="validate a compact leaderboard submission archive"
    )
    validate.add_argument("archive", type=Path)
    validate.set_defaults(handler=validate_submission)
    return root


def main() -> int:
    try:
        args = parser().parse_args()
        return int(args.handler(args))
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
