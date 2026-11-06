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
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import signal
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parent
TASKS_CSV = ROOT / "tasks" / "TASK_INVENTORY_47.csv"
EVALUATORS_CSV = ROOT / "evaluators" / "EVALUATOR_INDEX.csv"
TASK_EVALUATORS = ROOT / "evaluators" / "tasks"
PROMPT_TEMPLATE = ROOT / "AGENT_PROMPT.txt"


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
