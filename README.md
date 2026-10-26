<div align="center">

# ReproBoundary

**An Agent Capability Boundary Benchmark for Complex Paper-to-Code Reproduction**

[Task list](task_pool/TASK_INVENTORY_47.csv) ·
[Website](website/) ·
[Move to another machine](docs/PORTABILITY.md) ·
[Data description](docs/DATA_CARD.md)

</div>

<div align="center">
  <img src="website/assets/domain-distribution.png" width="100%" alt="Distribution of 47 ReproBoundary tasks across research domains">
</div>

ReproBoundary tests whether a coding agent can reproduce a specified experiment
from a research paper. For each paper, we select one experiment and state the
data, required steps, time limit, hardware limit, and result to report.

The benchmark has 47 paper tasks. We ran every task with nine combinations of a
language model and a coding agent, giving 423 runs in total.

## Repository contents

- [`task_pool/`](task_pool/) lists the 47 papers and the experiment selected
  from each paper.
- [`trajectories/`](trajectories/) contains one compressed execution log for
  each of the 423 runs. Credentials, private paths, and similar sensitive text
  have been removed or replaced.
- [`evaluators/`](evaluators/) contains the instructions and small helper files
  used to calculate the result for each task.
- [`protocol/`](protocol/) contains the prompt and task-file templates given to
  the agents.
- [`docs/`](docs/) explains the released files, file sources, licenses, log
  cleaning, release checks, and how to move an evaluator to another machine.
- [`website/`](website/) contains the benchmark homepage and the empty results
  table that will later be filled with checked experiment results.

The repository does not include datasets, trained model files, saved training
states, saved predictions, complete copies of other projects, credentials, or
private machine records. Download public data and code from the exact links and
versions listed in the task files.

## Quick start

The compressed logs are stored with [Git LFS](https://git-lfs.com/), which is a
Git extension for large files.

```bash
git lfs install
git clone https://github.com/endlesssalaxy/ReproBoundary.git
cd ReproBoundary
git lfs pull
```

Check that the files were downloaded correctly:

```bash
python3 scripts/verify_release.py
```

Expected output:

```text
verification OK: tasks=47 evaluators=47 trajectories=423
```

The check confirms the number of tasks, evaluation files, and logs. It also
checks file contents, size limits, and common credential formats.

## Task list

[`task_pool/TASK_INVENTORY_47.csv`](task_pool/TASK_INVENTORY_47.csv) is a plain
text table with one row per paper. Each row gives:

- paper title and research area;
- experiment to reproduce;
- result to report and the value reported by the paper;
- training or search work required by the benchmark;
- dataset and final test data;
- time, hardware, memory, and storage limits; and
- source-code link and exact code version.

Twenty tasks use the experiment size selected from the paper without reducing
the required work. For the other 27 tasks, training, search, or repeated work
was reduced to fit the resource limit. These 27 tasks still use the complete
final test data. They test one selected result and do not reproduce every result
in the source paper.

## Execution logs

Each run has one `agent.log.gz` file. The file records the agent's commands and
tool output in time order. The central file
[`TRAJECTORY_INDEX.csv`](trajectories/TRAJECTORY_INDEX.csv) links each log to
its paper task and model-agent combination.

The release has 418 completed run records, four logs whose final state is still
unclear, and one snapshot saved while a run was active. We keep these states as
recorded instead of guessing the missing outcomes.

## Checking a reported result

Each task has a `TARGET_EVALUATION.json` file. This file states which program to
run, which saved outputs it needs, which number to calculate, and how the result
must be written.

[`EVALUATOR_INDEX.csv`](evaluators/EVALUATOR_INDEX.csv) links every task to the
exact source-code version used for checking its result. Some included helper
files come from the original paper project, while others were written for
ReproBoundary to prepare inputs or combine repeated runs. See
[where the evaluator files came from](docs/EVALUATOR_PROVENANCE.md) before
describing a helper as original paper code.

Running the checking program again can confirm a submitted number. It does not
by itself confirm that the agent completed every required experiment step, so
the step checks and result checks are kept separate.

## Preview the website

```bash
python3 scripts/build_site_data.py
python3 -m http.server 8765 --directory website
```

Open `http://127.0.0.1:8765` in a browser.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). A change to a task, evaluation file, or
result must include a public source or saved evidence and the exact file or code
version that supports the change.

## License

No license has yet been selected for the files written by the ReproBoundary
team. Do not make the repository public until that license and all included
third-party files have been reviewed. Papers, datasets, models, source
repositories, and original evaluation programs keep their own licenses. See
[docs/LICENSES.md](docs/LICENSES.md).
