<div align="center">

# ReproBoundary

**An Agent Capability Boundary Benchmark for Complex Paper-to-Code Reproduction**

[![Website](https://img.shields.io/badge/website-reproboundary.github.io-12213f)](https://reproboundary.github.io/)
[![Dataset](https://img.shields.io/badge/Hugging%20Face-423%20trajectories-FFD21E)](https://huggingface.co/datasets/SupingSun/ReproBoundary-Execution-Trajectories)
[![Release check](https://img.shields.io/badge/release-verification%20script-197a66)](#download-and-verify-the-code-release)

[Task list](tasks/TASK_INVENTORY_47.csv) ·
[Trajectory dataset](https://huggingface.co/datasets/SupingSun/ReproBoundary-Execution-Trajectories) ·
[Website](https://reproboundary.github.io/) ·
[Frozen results](https://github.com/ReproBoundary/ReproBoundary.github.io/blob/main/data/leaderboard.json) ·
[Submit a run](SUBMIT_A_RUN.md) ·
[Evaluator guide](EVALUATOR_PROVENANCE.md)

</div>

ReproBoundary tests whether a coding agent can reproduce one specified
experiment from a research paper. Each task fixes the data, required stages,
result to report, and program used to check that result.

**Code and metadata live here; the 423 compressed trajectories live on
[Hugging Face](https://huggingface.co/datasets/SupingSun/ReproBoundary-Execution-Trajectories).**
This separation keeps the GitHub clone lightweight while preserving a fixed,
hash-verifiable data release.

> **Scope.** A task reproduces one selected result under a frozen task
> definition. It does not reproduce every result or support every conclusion
> in the source paper.

## At a glance

| Released material | Count | What it provides |
| --- | ---: | --- |
| Paper-reproduction tasks | 47 | One fixed experiment from each paper |
| Model-agent settings | 9 | Nine combinations of a language model and coding agent |
| Execution logs | 423 | Cleaned, compressed logs hosted in the separate Hugging Face dataset |
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
  [frozen aggregate](https://github.com/ReproBoundary/ReproBoundary.github.io/blob/main/data/leaderboard.json)
  maintained with the website source, and follow the
  [evidence-package submission guide](SUBMIT_A_RUN.md).

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
that no trajectory logs are bundled in the GitHub repository.

## Download and verify the trajectories

The 423 logs, paper PDFs, trajectory index, download command, and verification
instructions are maintained in the
[Hugging Face dataset](https://huggingface.co/datasets/SupingSun/ReproBoundary-Execution-Trajectories).

## Repository structure

`tasks/` defines the 47 frozen tasks, while `evaluators/` binds each task to its
target metric and checking files. The prompt, submission guide, license notes,
and evaluator provenance are kept as root-level files. The leaderboard is
maintained with the website source; papers, the trajectory index, and all 423
logs remain on Hugging Face. The project website is maintained separately at
[reproboundary.github.io](https://reproboundary.github.io/).

```text
ReproBoundary/
├── README.md
├── CONTRIBUTING.md
├── AGENT_PROMPT.txt
├── SUBMIT_A_RUN.md
├── LICENSES.md
├── EVALUATOR_PROVENANCE.md
├── RELEASE_MANIFEST.json
├── SHA256SUMS
├── verify_release.py
├── tasks/
│   └── TASK_INVENTORY_47.csv
└── evaluators/
    ├── EVALUATOR_INDEX.csv
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

## Execution logs

Every planned run has one cleaned `agent.log.gz` file in the separate
[trajectory dataset](https://huggingface.co/datasets/SupingSun/ReproBoundary-Execution-Trajectories).
GitHub does not duplicate the trajectory index or log files. Credentials,
private paths, authorization headers, cookies, and similar sensitive text have
been removed or replaced.

The archive contains 418 completed run records, four logs whose final state is
unresolved, and one snapshot saved while a run was active. These states are
preserved as recorded rather than converted into guessed outcomes.

## Evaluators

Every task has a `TARGET_EVALUATION.json` file describing the required outputs,
program to run, metric to calculate, and result format. The evaluator index
also fixes the source URL and exact code version.

Some helper files come from the source-paper repositories. Others were written
for ReproBoundary to prepare inputs, check completeness, or combine repeated
runs. [Evaluator file origins](EVALUATOR_PROVENANCE.md) identifies which
is which.

Recomputing a metric can confirm a submitted number. It does not by itself
prove that the agent completed every required experimental stage. Stage checks
and metric checks must therefore remain separate.

The trajectory dataset contains logs, not saved predictions, checkpoints,
model weights, or training states. The logs support chronology, tool-use,
failure, and release-integrity analysis. They are not sufficient by themselves
to recompute most task metrics.

## Not included

The GitHub release does not contain trajectory logs, datasets, trained model
files, saved training states, saved predictions, complete copies of third-party
projects, credentials, or private machine records. Download the trajectories
from the fixed Hugging Face dataset and public dependencies from the exact
links and versions recorded in the task and evaluator files.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). A change to a task, evaluator, or result
must include a public source or saved evidence and the exact file or code
version supporting the change.

## License

No top-level license has yet been selected for files written by the
ReproBoundary team. Public access does not by itself grant permission to copy,
modify, or redistribute those files. Papers, datasets, models, source
repositories, and original evaluation programs retain their own licenses. See
[`LICENSES.md`](LICENSES.md) before reuse.
