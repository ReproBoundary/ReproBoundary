# Moving an evaluator to another machine

This guide explains how to run a ReproBoundary evaluator on a machine that has
different paths, hardware, or job-control software.

An **evaluator** is the program that calculates a task's target metric from
saved outputs. Moving it to another machine is valid only when the move does
not change the data, model, metric, or required experimental stages.

## Two kinds of migration

Decide which kind you need before copying files.

1. **Scoring only:** calculate the target metric from predictions or other
   outputs that already exist.
2. **Full reproduction:** run every required experiment stage and then
   calculate the target metric.

Scoring only is not a full reproduction. A full reproduction may need Linux,
Bash, NVIDIA CUDA, the source-paper repository, datasets, model weights, and
the hardware listed in the task contract. **CUDA** is NVIDIA's software system
for running calculations on its GPUs.

## Files used during migration

- `evaluators/EVALUATOR_INDEX.csv` lists the evaluator source, exact version,
  command, contract hash, and included helper files.
- `evaluators/tasks/<project>/TARGET_EVALUATION.json` is the evaluation
  contract. A **contract** is a machine-readable record of what to run and how
  to score it.
- `REDUCTION_PROTOCOL/` contains small helper programs and configuration files
  for a resource-bounded task.
- `UPSTREAM_EVALUATOR/` contains evaluator files copied from an original
  project under a license that permits redistribution. **Upstream** means the
  original project maintained outside ReproBoundary.
- [`EVALUATOR_PROVENANCE.md`](EVALUATOR_PROVENANCE.md) states which files came
  from upstream projects and which were written for ReproBoundary.

Paths listed in `bundled_helper_files` start from the task directory. Run the
evaluator command from the root of the source-paper repository unless the
contract says otherwise.

## Step 1: Check the release before changing it

```bash
cd /path/to/ReproBoundary
python3 scripts/verify_release.py
```

This command checks file hashes, counts, indexes, size limits, and common
secret patterns. A **file hash** is a digital fingerprint used to detect a
changed file.

Keep the checked release unchanged. Perform the migration in a separate copy.

## Step 2: Choose one task

Set the release path and task ID, then print the task's evaluator information:

```bash
export RELEASE=/path/to/ReproBoundary
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

Record these values before continuing:

- source repository URL and commit ID;
- evaluator version;
- contract SHA-256 hash;
- dataset version and evaluation split;
- target metric, unit, and direction; and
- required hardware and time limit.

An **evaluation split** is the named part of a dataset used for scoring, such
as `test` or `validation`.

## Step 3: Download the exact source-code version

```bash
git clone <repository-url> worktree
git -C worktree checkout --detach <repository-commit>
```

The commit ID fixes one exact version of the repository. Do not replace it with
the current default branch, because that branch may have changed.

If the task uses a separate evaluation package, install the exact version in
`EVALUATOR_INDEX.csv`.

## Step 4: Copy the task helper files

Most tasks expect `REDUCTION_PROTOCOL/` at the root of the downloaded
source-paper repository:

```bash
cp -R \
  "$RELEASE/evaluators/tasks/$PROJECT_ID/REDUCTION_PROTOCOL" \
  worktree/
```

Keep original project files separate from files written for ReproBoundary.
Keep every `LICENSE` and `NOTICE.md` file.

If the new machine requires a code change, save the exact change. Also show
that the change does not alter the dataset, model, prompt, way of generating
answers, metric, or method for combining repeated scores. The last method is
called **aggregation**.

## Step 5: Download public data and models

Get large files from the public URLs and versions named in the contract or
`SOURCE_BINDINGS.json`. A **source binding** records the expected source and
version of an external file.

When a task provides a check script, run it. A matching filename is not enough.
The version, item count, order, IDs, and available hashes must also match.

Do not expose evaluation answers to the agent. Do not use them for training,
prompt writing, parameter selection, or debugging unless the task contract
explicitly allows that use.

## Step 6: Map old paths to new paths

Set the project, data, model, cache, and output paths to valid locations on the
new machine. Keep the expected directory contents unchanged.

`/input/task-config.json` is the contract file used by the benchmark container.
A **container** is an isolated software environment used to run a task. Outside
that container, create an unchanged equivalent file.

When an output asks for `target_contract_sha256`, calculate the SHA-256 hash of
the exact file bytes. Do not reformat the JSON first, because spacing changes
the file bytes and therefore changes the hash.

## Step 7: Map the hardware

If a launcher uses `CUDA_VISIBLE_DEVICES`, select one visible GPU:

```bash
export CUDA_VISIBLE_DEVICES=0
```

The physical GPU number does not matter. The following properties do matter:

- model and model version;
- numerical precision, such as 16-bit or 32-bit numbers;
- batch meaning and batch size;
- number of visible GPUs;
- work required at each stage; and
- time limit.

Use replacement hardware only when the contract permits an equivalent hardware
class and the full task still meets every fixed requirement.

The helper shell scripts expect Linux and Bash. Package or CUDA repairs are
allowed only when they keep the same data, calculations, answer generation,
metric, and aggregation. Record every repair.

## Step 8: Run the evaluator

From the downloaded repository root, run the command stored in
`evaluator.command` inside `TARGET_EVALUATION.json`.

Save:

- standard output and standard error, which are the program's normal and error
  text streams;
- exit status, where zero normally means success;
- running time;
- input and output hashes; and
- exact package versions.

For a full reproduction, also keep evidence for every required pipeline stage.
A **pipeline stage** is one required part of the experiment, such as data
preparation, training, inference, or scoring. A metric from a run that skipped
a required stage is not a valid full reproduction.

## Step 9: Check the migrated result

Accept the migrated evaluator only when all relevant checks pass:

- repository and evaluator versions match the index;
- the contract hash matches `contract_sha256`;
- required input hashes, item counts, IDs, and order match;
- evaluation split, prompt, answer mapping, metric, unit, and aggregation are
  unchanged;
- the evaluator exits successfully and writes the required output format;
- another evaluator run can calculate the same target metric from the saved
  outputs; and
- the run did not access test answers, change the evaluator, read credentials,
  or use a forbidden resource.

If a difference cannot be resolved, record it as a task-rule difference. Do
not silently accept it.

## Notes for specific tasks

- **Task 017:** `UPSTREAM_EVALUATOR/` contains evaluator files under the MIT
  License. Copy them into the fixed source-paper checkout. Download WinoBias
  data and model weights separately.
- **Task 019:** the release contains ReproBoundary wrappers for SinkTrack
  inference and three-seed aggregation. A **seed** is a fixed number used to
  control random choices. Download the original SinkTrack `eval.py` from the
  pinned source URL. It is not copied here because its repository has no
  declared license.
- **Task 118:** copy the CC BY 4.0 evaluator files into the fixed
  CausalDiagnosticity checkout. `NOTICE.md` records the changes used to fix
  model and dataset versions.
- **LinearPatch:** install the source-paper version of
  `lm-evaluation-harness` 0.4.4. The fixed ARC-Easy helper keeps the prompt,
  answer mapping, choice order, all test questions, and raw accuracy.

## Limits

- One software container cannot run all 47 projects because some projects need
  incompatible Python or CUDA versions.
- Some source repositories assume Linux tools or a specific directory layout.
- Equivalent GPUs may produce small numerical differences because of hardware
  and software behavior. Report the full hardware and software setup.
- Matching sources and task rules does not prove that two evaluator programs
  always return the same number. That stronger claim requires a regression
  test, which runs both programs on the same fixed inputs and compares outputs.
