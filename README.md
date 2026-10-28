<div align="center">

# ReproBoundary

**An Agent Capability Boundary Benchmark for Complex Paper-to-Code Reproduction**

[Task list](task_pool/TASK_INVENTORY_47.csv) ·
[Website](website/) ·
[Data description](docs/DATA_CARD.md) ·
[Evaluator guide](docs/EVALUATOR_PROVENANCE.md) ·
[Migration guide](docs/PORTABILITY.md)

</div>

<div align="center">
  <img src="website/assets/domain-distribution.png" width="760" alt="Distribution of 47 ReproBoundary tasks across research areas">
</div>

ReproBoundary tests whether a coding agent can reproduce one specified
experiment from a research paper. Each task fixes the data, required stages,
resource limits, result to report, and program used to check that result.

> **Scope.** A task reproduces one selected result under a fixed resource
> limit. It does not reproduce every result or support every conclusion in the
> source paper.

## At a glance

| Released material | Count | What it provides |
| --- | ---: | --- |
| Paper-reproduction tasks | 47 | One fixed experiment from each paper |
| Model-agent settings | 9 | Nine combinations of a language model and coding agent |
| Execution logs | 423 | One cleaned, compressed log for every planned run |
| Evaluator records | 47 | The exact metric, command, source, and version for each task |

Twenty tasks keep the experiment size selected from the paper. The other 27
reduce training, search, or repeated work to fit the benchmark resource limit.
All 47 tasks retain their complete target evaluation set.

## Start here

- **Browse the papers and tasks:**
  [`TASK_INVENTORY_47.csv`](task_pool/TASK_INVENTORY_47.csv) is the readable
  table; [`tasks.jsonl`](task_pool/tasks.jsonl) contains the same task records
  in a machine-readable format.
- **Study an agent run:**
  [`TRAJECTORY_INDEX.csv`](trajectories/TRAJECTORY_INDEX.csv) links every task
  and model-agent setting to its `agent.log.gz` file.
- **Check a submitted result:**
  [`EVALUATOR_INDEX.csv`](evaluators/EVALUATOR_INDEX.csv) identifies the
  evaluation command, source-code version, and required helper files.
- **Move an evaluator to another machine:** follow the
  [migration guide](docs/PORTABILITY.md) without changing the task's data,
  method, or metric.

## Download and verify

The compressed logs use [Git LFS](https://git-lfs.com/), a Git extension for
large files.

```bash
git lfs install
git clone https://github.com/endlesssalaxy/ReproBoundary.git
cd ReproBoundary
git lfs pull
python3 scripts/verify_release.py
```

Expected output:

```text
verification OK: tasks=47 evaluators=47 trajectories=423
```

This check confirms file hashes, index entries, size limits, task and evaluator
counts, all 423 logs, and common credential patterns.

## Repository map

| Path | Contents |
| --- | --- |
| [`task_pool/`](task_pool/) | Paper list, selected experiments, reported reference values, datasets, budgets, and pinned source-code versions |
| [`trajectories/`](trajectories/) | Cleaned execution logs and the index connecting each log to its task and model-agent setting |
| [`evaluators/`](evaluators/) | Per-task evaluation instructions and small helper files used to calculate the target metric |
| [`protocol/`](protocol/) | Prompt and task-file templates given to the agents |
| [`docs/`](docs/) | Data scope, file sources, licenses, cleaning rules, release checks, and evaluator migration instructions |
| [`website/`](website/) | Benchmark homepage and an unpublished leaderboard placeholder |

## Task definitions

Each row in [`TASK_INVENTORY_47.csv`](task_pool/TASK_INVENTORY_47.csv) records:

- the paper title and research area;
- the selected experiment and result to report;
- the value reported by the paper;
- paper-scale and benchmark-scale work;
- dataset and final evaluation data;
- time, hardware, memory, and storage limits; and
- source repository and exact code version.

The reduced tasks change only the amount of training, search, or repeated work
allowed by their fixed specification. They still test one selected result on
the complete target evaluation set.

## Execution logs

Every planned run has one cleaned `agent.log.gz` file. Credentials, private
paths, authorization headers, cookies, and similar sensitive text have been
removed or replaced.

The archive contains 418 completed run records, four logs whose final state is
unresolved, and one snapshot saved while a run was active. These states are
preserved as recorded rather than converted into guessed outcomes.

## Evaluators

Every task has a `TARGET_EVALUATION.json` file describing the required outputs,
program to run, metric to calculate, and result format. The evaluator index
also fixes the source URL and exact code version.

Some helper files come from the source-paper repositories. Others were written
for ReproBoundary to prepare inputs, check completeness, or combine repeated
runs. [Evaluator file origins](docs/EVALUATOR_PROVENANCE.md) identifies which
is which.

Recomputing a metric can confirm a submitted number. It does not by itself
prove that the agent completed every required experimental stage. Stage checks
and metric checks must therefore remain separate.

## Preview the website

```bash
python3 scripts/build_site_data.py
python3 -m http.server 8765 --directory website
```

Open `http://127.0.0.1:8765` in a browser. The repository does not currently
publish leaderboard results; the page contains a placeholder only.

## Not included

The release does not contain datasets, trained model files, saved training
states, saved predictions, complete copies of third-party projects,
credentials, or private machine records. Download public dependencies from the
exact links and versions recorded in the task and evaluator files.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). A change to a task, evaluator, or result
must include a public source or saved evidence and the exact file or code
version supporting the change.

## License

No license has yet been selected for files written by the ReproBoundary team.
Do not make the repository public until that license and all included
third-party files have been reviewed. Papers, datasets, models, source
repositories, and original evaluation programs retain their own licenses. See
[`docs/LICENSES.md`](docs/LICENSES.md).
