<div align="center">

# ReproBoundary

**How Reliably Can Coding Agents Reproduce AI Research Papers?**

[![Website](https://img.shields.io/badge/website-reproboundary.github.io-12213f)](https://reproboundary.github.io/)
[![Dataset](https://img.shields.io/badge/Hugging%20Face-423%20execution%20traces-FFD21E)](https://huggingface.co/datasets/SupingSun/ReproBoundary-Execution-Trajectories)
[![Tasks](https://img.shields.io/badge/tasks-47-197a66)](tasks/TASK_INVENTORY_47.csv)

[Quick start](#quick-start) ·
[Benchmark contents](#benchmark-contents) ·
[Run manually](#run-the-steps-manually) ·
[Submit a result](#submit-a-result) ·
[Website](https://reproboundary.github.io/)

</div>

ReproBoundary tests whether coding agents can carry out one fixed reproduction
task from each of 47 AI research papers and produce evidence that can be
checked independently. Each task fixes the source commit, data scope, pipeline,
target metric, and evaluator before the agent starts.

> **Scope.** ReproBoundary measures agent performance on these fixed tasks. It
> does not claim to reproduce every full-scale result in the source papers.

## Overview

| Released material | Count | Location |
| --- | ---: | --- |
| Paper-reproduction tasks | 47 | [`tasks/`](tasks/) |
| Model–agent configurations | 9 | [Paper results](https://reproboundary.github.io/#leaderboard) |
| Frozen evaluators | 47 | [`evaluators/`](evaluators/) |
| Compressed execution traces | 423 | [Hugging Face](https://huggingface.co/datasets/SupingSun/ReproBoundary-Execution-Trajectories) |

A run follows four steps:

1. Load the selected paper, frozen contract, and pinned source commit.
2. Let the coding agent execute the required reproduction pipeline.
3. Run the task's frozen evaluator on the produced artifacts.
4. Package the result, evidence, log, and source changes for review.

## Quick start

Install Git, Python 3, and an authenticated Codex CLI, then run:

```bash
git clone --depth 1 https://github.com/ReproBoundary/ReproBoundary.git && cd ReproBoundary && python3 pipeline.py run 016-2025.emnlp.109 --agent codex
```

The command downloads and verifies the matching paper, checks out the frozen
source commit, runs the agent, launches the evaluator, and stores everything in
a timestamped directory under `runs/`.

The 43 redistributable papers come from the Hugging Face dataset. The other
four papers are downloaded locally from their official arXiv links and are not
redistributed in the dataset.

To use another non-interactive coding agent:

```bash
python3 pipeline.py run "$PROJECT_ID" --agent-command "your-agent --non-interactive"
```

The prompt is sent on standard input. Use `--no-prompt-stdin` only if the agent
reads the path in `REPROBOUNDARY_PROMPT` itself.

## Run the steps manually

Use the separate commands when debugging or integrating another runner:

```bash
python3 pipeline.py show "$PROJECT_ID"
python3 pipeline.py prepare-run "$PROJECT_ID" --output "runs/$PROJECT_ID" --clone-source --paper /path/to/paper.pdf
python3 pipeline.py infer --run-dir "runs/$PROJECT_ID" -- your-agent --non-interactive
python3 pipeline.py evaluate --run-dir "runs/$PROJECT_ID"
```

To export machine-readable records from all released task and evaluator
contracts:

```bash
python3 pipeline.py export-dataset --output build/reproboundary
```

Task-specific models, datasets, dependencies, GPU requirements, and time limits
are defined in each `TARGET_EVALUATION.json`. The runner prepares the task but
does not install every paper's scientific dependencies.

## Benchmark contents

The three public parts are linked rather than duplicated:

- **GitHub:** task contracts, evaluator records, the agent prompt, and the
  runner.
- **Hugging Face:** paper index, 43 redistributable PDFs, trajectory index, and
  423 compressed execution traces.
- **Website:** paper results, task explorer, failure analysis, and result
  submission instructions.

The authoritative catalogs are:

- [`TASK_INVENTORY_47.csv`](tasks/TASK_INVENTORY_47.csv): paper, selected
  experiment, target metric, dataset, source repository, and frozen commit.
- [`EVALUATOR_INDEX.csv`](evaluators/EVALUATOR_INDEX.csv): evaluator command,
  source, version, contract hash, and helper files.
- [`TRAJECTORY_INDEX.csv`](https://huggingface.co/datasets/SupingSun/ReproBoundary-Execution-Trajectories/blob/main/trajectories/TRAJECTORY_INDEX.csv): one record for each released execution trace.

### Repository structure

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

[`EVALUATOR_PROVENANCE.md`](evaluators/EVALUATOR_PROVENANCE.md) records which
evaluator files came from source-paper repositories and which were created for
ReproBoundary.

## Submit a result

After the run has produced the six files required by its contract, create and
check one compact archive:

```bash
MODEL=your-model AGENT=your-agent
python3 pipeline.py pack-submission --run-dir "runs/$PROJECT_ID" --model "$MODEL" --agent "$AGENT" --output "$PROJECT_ID-$MODEL-$AGENT.tar.gz"
python3 pipeline.py validate-submission "$PROJECT_ID-$MODEL-$AGENT.tar.gz"
```

```text
<project-id>-<model>-<agent>/
├── submission.json
├── artifacts/
├── agent.log.gz
└── source.patch        # only when source files changed
```

`submission.json` embeds the six contract-required deliverables without
changing their frozen schemas. The complete field reference, generated-file
template, example, and delivery instructions are in
[`SUBMIT_A_RUN.md`](https://github.com/ReproBoundary/ReproBoundary.github.io/blob/main/SUBMIT_A_RUN.md).

## Verify the release

```bash
python3 verify_release.py
```

Expected output:

```text
verification OK: tasks=47 evaluators=47 bundled_logs=0
```

This checks the release hashes, task and evaluator counts, evaluator size
limits, and confirms that execution logs are not duplicated in GitHub.

## Evidence limits

- Execution traces record what the agent did, but the Hugging Face release does
  not include saved predictions, checkpoints, model weights, or training states.
- The public runner does not recreate the paper's separate evidence-only agent
  session or host-side stage verification.
- Some evaluators call upstream files inside the agent-controlled source tree.
  A local metric replay alone therefore does not establish strict reproduction
  success; submitted packages are reviewed separately.
- Credentials, private machine paths, datasets, model files, and complete
  third-party repositories are not included.

## License

No top-level license has yet been selected for files written by the
ReproBoundary team. Public access does not itself grant permission to copy,
modify, or redistribute those files. Papers, datasets, models, source
repositories, and original evaluator programs retain their own licenses. See
[`LICENSES.md`](LICENSES.md) before reuse.
