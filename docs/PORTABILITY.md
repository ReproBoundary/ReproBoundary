# Evaluator portability and migration

This guide explains how to move a ReproBoundary evaluator to a machine that
does not use the original benchmark filesystem or scheduler. The release is
lightweight: it contains contracts, small scripts, configurations, and
answer-free membership manifests. It does not contain model weights, datasets,
checkpoints, predictions, complete third-party repositories, or private host
records.

## What can be migrated

There are two different migration targets:

1. **Scoring only.** Run the frozen metric implementation on already produced
   predictions or artifacts. This is usually CPU-portable unless the upstream
   evaluator itself requires a framework-specific GPU operation.
2. **Full reproduction pipeline.** Run every required method stage and then
   score its output. This may require Linux, Bash, NVIDIA CUDA, the paper's
   repository, model weights, datasets, and the hardware envelope recorded in
   `TARGET_EVALUATION.json`.

Do not describe a scoring-only migration as a full reproduction. A valid
reproduction still requires all stages, data scopes, budgets, and provenance
checks in the frozen contract.

## Package roles

- `evaluators/EVALUATOR_INDEX.csv` maps each project to its evaluator source,
  pinned version, frozen command, contract hash, and bundled files.
- `evaluators/tasks/<project>/TARGET_EVALUATION.json` is the authoritative
  task contract.
- `REDUCTION_PROTOCOL/` contains small launchers, adapters, validators, and
  frozen configuration or membership files.
- `UPSTREAM_EVALUATOR/` contains a licensed upstream evaluation-code subset.
- `docs/EVALUATOR_PROVENANCE.md` distinguishes original project code from
  benchmark-authored wrappers.

Paths in `bundled_helper_files` are relative to the corresponding task
directory. Commands in `TARGET_EVALUATION.json` are normally executed from
the root of a pinned checkout of the paper repository.

## Migration procedure

### 1. Verify the untouched release

```bash
cd /path/to/reproboundary-open-source-20261020
python3 scripts/verify_release.py
```

Perform this check before copying or modifying any file. Work from a separate
checkout so that the release hashes remain verifiable.

### 2. Select one frozen task

Set the task identifier and inspect both the central index and contract:

```bash
export RELEASE=/path/to/reproboundary-open-source-20261020
export PROJECT_ID=2025.neurips.e323ebf7c91a4ca061612ba4a2f2164d

python3 - "$RELEASE" "$PROJECT_ID" <<'PY'
import csv, json, pathlib, sys

release = pathlib.Path(sys.argv[1])
project = sys.argv[2]
rows = csv.DictReader((release / "evaluators/EVALUATOR_INDEX.csv").open())
row = next(item for item in rows if item["project_id"] == project)
contract = json.loads(
    (release / "evaluators/tasks" / project / "TARGET_EVALUATION.json").read_text()
)
print(json.dumps(row, indent=2))
print(json.dumps(contract["evaluator"], indent=2))
PY
```

Record the repository URL and commit, evaluator version, contract SHA-256,
dataset revisions, target split, metric key, direction, and unit.

### 3. Materialize the pinned upstream source

Clone the task repository into a clean working directory and check out the
exact commit from the task inventory. Do not use the repository's default
branch as a substitute for the pinned revision.

```bash
git clone <repository-url> worktree
git -C worktree checkout --detach <repository-commit>
```

If the evaluator comes from a separate standard harness, fetch the exact
version in `EVALUATOR_INDEX.csv` as an additional dependency.

### 4. Overlay the bundled helper layer

For the usual task layout, copy `REDUCTION_PROTOCOL/` into the root of the
pinned repository checkout:

```bash
cp -R \
  "$RELEASE/evaluators/tasks/$PROJECT_ID/REDUCTION_PROTOCOL" \
  worktree/
```

Keep upstream files and benchmark-authored helpers distinguishable. Preserve
all `LICENSE` and `NOTICE.md` files. Do not silently edit a frozen helper; if a
platform repair is necessary, record its diff and show that it does not change
the dataset, model, prompt, decoding, metric, or aggregation.

### 5. Materialize public assets

Obtain datasets, models, and other large assets from the pinned public URLs in
the contract or `SOURCE_BINDINGS.json`. Run the bundled source verifier when
present. A matching filename is not sufficient; revisions, counts, ordering,
and hashes must match.

Keep evaluation answers and labels inside the evaluator boundary. They must
not be used for method selection, calibration, training, prompt construction,
or debugging unless the contract explicitly permits that use.

### 6. Map paths without changing semantics

The helpers contain no ReproBoundary-internal absolute filesystem paths.
Project roots, asset roots, caches, and output roots are either relative paths
or task-specific environment variables. Point those variables to local
locations while preserving the expected directory contents.

`/input/task-config.json` is the benchmark container interface. Outside the
container harness, create an equivalent immutable task-config file and use its
exact byte-level SHA-256 wherever the output schema requests
`target_contract_sha256`. Do not replace it with a reformatted JSON hash.

### 7. Map compute resources

When a launcher requires `CUDA_VISIBLE_DEVICES`, assign one visible device:

```bash
export CUDA_VISIBLE_DEVICES=0
```

The physical GPU index is not scientifically meaningful. Model type,
precision, batch semantics, stage budgets, and the number of visible devices
are meaningful and must follow the contract. Use substitute hardware only
when the contract allows an equivalent class and the complete pipeline still
meets the frozen protocol.

Shell launchers assume a Linux/Bash environment. Python packages and CUDA
libraries must remain compatible with the pinned upstream implementation.
Dependency repairs are acceptable only when they preserve tensor, data,
decoding, and metric semantics and are documented.

### 8. Run from the expected working directory

Execute the command array in the contract's `evaluator.command` from the
pinned repository root. Preserve stdout, stderr, exit status, runtime, input
hashes, output hashes, and exact package versions.

For full reproduction, retain evidence for every `pipeline_stages` entry. A
metric produced after skipping or replacing a required stage is not a valid
reproduction result.

### 9. Validate the migrated result

A migrated evaluator is accepted only when all applicable checks pass:

- upstream repository and evaluator versions match the index;
- the contract file matches `contract_sha256`;
- required input hashes, sample counts, IDs, and order match;
- the target split, prompt, choice mapping, metric, unit, and aggregation are
  unchanged;
- the evaluator exits successfully and produces the required output schema;
- the reported target metric can be independently replayed from the submitted
  artifacts;
- no forbidden test-label, evaluator-modification, credential, or resource
  access occurred.

Environment portability does not relax scientific comparability. Record any
unresolved difference as a protocol deviation rather than silently accepting
the result.

## Task-specific notes

- **017:** `UPSTREAM_EVALUATOR/` contains the MIT-licensed evaluation-code
  subset. Overlay it into the pinned project checkout. WinoBias data and model
  weights must be acquired separately.
- **019:** the release includes benchmark-authored SinkTrack inference and
  three-seed aggregation wrappers. Obtain the original SinkTrack `eval.py`
  from the pinned source URL; it is not redistributed because the frozen
  upstream repository has no declared license.
- **118:** overlay the CC BY 4.0 evaluation-code subset into the pinned
  CausalDiagnosticity checkout. The bundled `eval.py` adds explicit model and
  dataset revision arguments; its modification and hashes are recorded in
  `NOTICE.md`.
- **LinearPatch:** install the paper-specified `lm-evaluation-harness` 0.4.4
  commit. The frozen ARC-Easy template changes only the task name and local,
  hash-verified dataset binding; prompt, answer mapping, choice order, and
  `acc` aggregation remain unchanged.

## Known portability limits

- The release does not provide one universal container for all 47 projects.
- Full pipelines may require incompatible Python or CUDA dependency stacks.
- Some upstream repositories assume Linux utilities or a specific directory
  structure.
- Hardware-equivalent execution does not guarantee identical floating-point
  outputs; report the software and hardware stack with the result.
- Source and protocol equivalence do not replace an independent numerical
  regression test for a third-party evaluator.
