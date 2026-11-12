<div align="center">

# ReproBoundary

**How Reliably Can Coding Agents Reproduce AI Research Papers?**

[![Website](https://img.shields.io/badge/website-reproboundary.github.io-12213f)](https://reproboundary.github.io/)
[![Dataset](https://img.shields.io/badge/Hugging%20Face-423%20execution%20traces-FFD21E)](https://huggingface.co/datasets/SupingSun/ReproBoundary-Execution-Trajectories)
[![Release check](https://img.shields.io/badge/release-verification%20script-197a66)](#download-and-verify-the-code-release)

[Task list](tasks/TASK_INVENTORY_47.csv) ·
[Execution-trace dataset](https://huggingface.co/datasets/SupingSun/ReproBoundary-Execution-Trajectories) ·
[Website](https://reproboundary.github.io/) ·
[Paper results](https://github.com/ReproBoundary/ReproBoundary.github.io/blob/main/data/leaderboard.json) ·
[Submit a run](https://github.com/ReproBoundary/ReproBoundary.github.io/blob/main/SUBMIT_A_RUN.md) ·
[Evaluator guide](evaluators/EVALUATOR_PROVENANCE.md)

</div>

ReproBoundary evaluates whether coding agents can carry out specified
paper-reproduction tasks and submit independently verifiable results. Each task
fixes execution and evaluation requirements before agent runs.

**Code and metadata live here; the 423 compressed execution traces live on
[Hugging Face](https://huggingface.co/datasets/SupingSun/ReproBoundary-Execution-Trajectories).**
This separation keeps the GitHub clone lightweight; the dataset records file
hashes for the released execution traces.

> **Scope.** Our findings concern agent performance on the fixed benchmark
> tasks, not the reproducibility of the papers' full-scale results.

## At a glance

| Released material | Count | What it provides |
| --- | ---: | --- |
| Paper-reproduction tasks | 47 | One fixed experiment from each paper |
| Model–agent configurations | 9 | Nine configurations across five base models |
| Execution traces | 423 | Released, compressed records hosted in the separate Hugging Face dataset |
| Evaluator records | 47 | The exact metric, command, source, and version for each task |

All 47 tasks retain their complete target evaluation set.

## Start here

- **Browse the papers and tasks:**
  [`TASK_INVENTORY_47.csv`](tasks/TASK_INVENTORY_47.csv) is the single
  authoritative task catalog and is directly machine-readable.
- **Study an agent run:**
  use the [`TRAJECTORY_INDEX.csv`](https://huggingface.co/datasets/SupingSun/ReproBoundary-Execution-Trajectories/blob/main/trajectories/TRAJECTORY_INDEX.csv)
  stored with the logs on Hugging Face.
- **Check a submitted result:**
  [`EVALUATOR_INDEX.csv`](evaluators/EVALUATOR_INDEX.csv) identifies the
  evaluation command, source-code version, and required helper files.
- **Read or submit leaderboard results:** inspect the
  [paper main-results table](https://github.com/ReproBoundary/ReproBoundary.github.io/blob/main/data/leaderboard.json)
  maintained with the website source, and follow the
  [evidence-package submission guide](https://github.com/ReproBoundary/ReproBoundary.github.io/blob/main/SUBMIT_A_RUN.md).

## Export, infer, and evaluate

[`pipeline.py`](pipeline.py) provides one standard-library entry point for the
released workflow. First export the machine-readable dataset from all 47
frozen task and evaluator contracts:

```bash
python3 pipeline.py export-dataset --output build/reproboundary
```

To run one task, download its paper from the
[execution-trace dataset](https://huggingface.co/datasets/SupingSun/ReproBoundary-Execution-Trajectories/tree/main/task_pool),
then prepare the pinned source tree and task files:

```bash
PROJECT_ID=016-2025.emnlp.109
hf download SupingSun/ReproBoundary-Execution-Trajectories \
  "task_pool/${PROJECT_ID}.pdf" --repo-type dataset --local-dir build/papers
python3 pipeline.py prepare-run "$PROJECT_ID" \
  --output "runs/$PROJECT_ID" --clone-source \
  --paper "build/papers/task_pool/${PROJECT_ID}.pdf"
python3 pipeline.py show "$PROJECT_ID"
```

Pass the generated prompt to a coding agent. This Codex example can be replaced
by another non-interactive agent command; `pipeline.py` records the command and
combined output under `runs/<project_id>/logs/`:

```bash
python3 pipeline.py infer --run-dir "runs/$PROJECT_ID" -- \
  codex exec --sandbox workspace-write -
```

After the run has produced the contract-required artifacts, execute the exact
frozen command from `EVALUATOR_INDEX.csv` as a local replay:

```bash
python3 pipeline.py evaluate --run-dir "runs/$PROJECT_ID"
```

Package the six contract-required deliverables, their referenced artifacts,
the compressed agent log, and any source change into one compact submission:

```bash
MODEL=your-model AGENT=your-agent
python3 pipeline.py pack-submission --run-dir "runs/$PROJECT_ID" --model "$MODEL" --agent "$AGENT" --output "$PROJECT_ID-$MODEL-$AGENT.tar.gz"
python3 pipeline.py validate-submission "$PROJECT_ID-$MODEL-$AGENT.tar.gz"
```

The archive has only `submission.json`, `artifacts/`, `agent.log.gz`, and an
optional `source.patch` at its top level. `submission.json` embeds the original
six v4 deliverables without replacing their frozen schemas. See the
[submission guide](https://github.com/ReproBoundary/ReproBoundary.github.io/blob/main/SUBMIT_A_RUN.md)
for the upload and email fields.

Use `infer --dry-run` or `evaluate --dry-run` to inspect a command without
executing it. Task-specific models, datasets, dependencies, GPU resources, and
time limits are defined in `TARGET_EVALUATION.json`; preparing a run does not
download those scientific dependencies. For the four link-only papers, follow
their official URLs in the dataset's `PAPER_INDEX.csv` instead of the `hf
download` command above.

`infer` is limited to the contract's `experiment_seconds`; an optional
`--timeout-seconds` must be positive and cannot exceed that limit. This public
helper runs one agent process. It does not implement the separate agent session
of up to one hour that the paper's experimental setup allows for organizing and
submitting existing artifacts.

`export-dataset` exports runnable records from the already reviewed release. It
does not automate the paper screening, human verification, or task approval
used to construct the benchmark.

This CLI does not reproduce the complete evaluation setup described in the
paper. `evaluate`
re-derives the command from the released evaluator index and verifies every
bundled helper file before running it, but some tasks also call upstream
evaluator files inside the agent-controlled source tree. The CLI does not
isolate those upstream files or reproduce host-side stage verification.
Running it alone therefore does not establish the paper's execution-success
criterion. Leaderboard submissions still require the separate package review
linked above.

## Download and verify the code release

```bash
git clone https://github.com/ReproBoundary/ReproBoundary.git
cd ReproBoundary
python3 verify_release.py
```

Expected output:

```text
verification OK: tasks=47 evaluators=47 bundled_logs=0
```

This checks file hashes, task and evaluator counts, evaluator size limits, and
that no execution-trace logs are bundled in the GitHub repository.

## Download and verify the execution traces

The 423 execution traces, paper PDFs, index, download command, and verification
instructions are maintained in the
[Hugging Face dataset](https://huggingface.co/datasets/SupingSun/ReproBoundary-Execution-Trajectories).

## Repository structure

`tasks/` defines the 47 frozen tasks, while `evaluators/` binds each task to its
target metric, provenance, and checking files. The prompt and license notes are
kept as root-level files. The leaderboard and submission guide are maintained
with the website source; papers, the execution-trace index, and all 423 logs remain
on Hugging Face. The project website is maintained separately at
[reproboundary.github.io](https://reproboundary.github.io/).

```text
ReproBoundary/
├── README.md
├── AGENT_PROMPT.txt
├── LICENSES.md
├── SHA256SUMS
├── pipeline.py
├── verify_release.py
├── tasks/
│   └── TASK_INVENTORY_47.csv
└── evaluators/
    ├── EVALUATOR_INDEX.csv
    ├── EVALUATOR_PROVENANCE.md
    └── tasks/
        └── <project_id>/
            ├── TARGET_EVALUATION.json
            └── <task-specific evaluator files>
```

## Task definitions

Each row in [`TASK_INVENTORY_47.csv`](tasks/TASK_INVENTORY_47.csv) records:

- the paper title and research area;
- the selected experiment and result to report;
- the value reported by the paper;
- dataset and final evaluation data;
- source repository and exact code version.

Execution requirements remain in each task-specific evaluation contract rather
than being duplicated in the central task catalog.

## Execution traces

Every planned run has one released `agent.log.gz` file in the separate
[execution-trace dataset](https://huggingface.co/datasets/SupingSun/ReproBoundary-Execution-Trajectories).
GitHub does not duplicate the execution-trace index or log files. Credentials,
private paths, authorization headers, cookies, and similar sensitive text have
been removed or replaced.

## Evaluators

Every task has a `TARGET_EVALUATION.json` file describing the required outputs,
program to run, metric to calculate, and result format. The evaluator index
also fixes the source URL and exact code version.

Some helper files come from the source-paper repositories. Others were written
for ReproBoundary to prepare inputs, check completeness, or combine repeated
runs. [Evaluator file origins](evaluators/EVALUATOR_PROVENANCE.md) identifies which
is which.

Rerunning an evaluator on retained outputs verifies the reported metric against
those outputs; it does not, by itself, establish how they were produced. The
paper therefore assesses process evidence and metric agreement separately.

The execution-trace dataset contains execution traces, not saved predictions,
checkpoints, model weights, or training states. Execution records provide
evidence that required stages ran, but they cannot prove that every
implementation detail matches the paper. They are not sufficient by themselves
to recompute most task metrics.

## Not included

The GitHub release does not contain execution traces, datasets, trained model
files, saved training states, saved predictions, complete copies of third-party
projects, credentials, or private machine records. Download the execution traces
from the fixed Hugging Face dataset and public dependencies from the exact
links and versions recorded in the task and evaluator files.

## License

No top-level license has yet been selected for files written by the
ReproBoundary team. Public access does not by itself grant permission to copy,
modify, or redistribute those files. Papers, datasets, models, source
repositories, and original evaluation programs retain their own licenses. See
[`LICENSES.md`](LICENSES.md) before reuse.
