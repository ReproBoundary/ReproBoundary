# Data card

This file explains what the release contains, what it leaves out, and how the
files may be used. A **data card** is a short record of a dataset's contents,
source, intended use, and limits.

## Size and unit of analysis

The release has 47 paper-reproduction tasks and nine model-agent settings. A
**model-agent setting** is one language model paired with one coding-agent
program. Pairing every task with every setting gives 423 planned runs.

The saved archive has the following run records. An evidence bundle is the
saved set of logs and output files for one run.

- 418 completed evidence bundles;
- four raw logs whose final state is unresolved; and
- one snapshot saved while a run was active.

The release keeps these states as recorded. It does not guess missing outcomes.

## Task records

Each task record includes:

- source paper and research domain;
- target experiment and target metric;
- value reported by the paper;
- paper-scale and benchmark-scale work;
- final evaluation data;
- time, hardware, memory, and storage limits;
- source repository and exact commit ID; and
- a hash of the evaluation contract.

A **commit ID** names one exact version of a Git repository. A **hash** is a
digital fingerprint used to detect a changed file.

Twenty-seven tasks reduce training, search, or repeated work to fit the fixed
resource limit. They keep the complete target evaluation set. These tasks test
one fixed claim under a fixed budget; they do not reproduce all claims in the
source paper.

## Execution logs

The large execution logs are stored in the separate
[Hugging Face trajectory dataset](https://huggingface.co/datasets/SupingSun/ReproBoundary-Execution-Trajectories)
at revision `57e17e11f795c6df9f7806ad2262fd32897ec2e6`. The GitHub repository keeps
the small [`TRAJECTORY_INDEX.csv`](../trajectories/TRAJECTORY_INDEX.csv), which
links every log to its task and model-agent setting. The dataset provides one
cleaned `agent.log.gz` file for each planned run.

The logs have been **redacted**, meaning that detected credentials, private
paths, authorization headers, cookies, and similar sensitive text were
replaced. The release does not include:

- raw machine security records;
- raw requests or responses from model providers;
- machine names and private absolute paths;
- credentials; or
- the other per-run files in the protected archive.

The cleaned log is therefore not byte-for-byte identical to the protected
original. The index stores separate SHA-256 hashes for the source and released
files. SHA-256 is the hash method used to create each digital fingerprint.

## Evaluation files

[`EVALUATOR_INDEX.csv`](../evaluators/EVALUATOR_INDEX.csv) lists the evaluator
source, exact version, command, contract hash, and included helper files for
each task. An **evaluator** is the program that calculates the target metric
from a run's saved outputs.

The release includes licensed parts of the original evaluators for tasks 017
and 118. Task 019 includes small wrappers written for ReproBoundary. A
**wrapper** is a small program that prepares inputs or calls another program;
it does not replace the original metric calculation.

The release does not copy the unlicensed SinkTrack evaluator or any complete
third-party repository. See [Evaluator file origins](EVALUATOR_PROVENANCE.md)
for details.

## Size limits

Evaluation files are kept small so that users can inspect them easily. The
release check rejects:

- any single evaluator file larger than 1 MiB; or
- all evaluator files together larger than 10 MiB.

MiB means mebibyte, or 1,048,576 bytes. Datasets, trained model files, saved
training states, and saved predictions are not part of the evaluator package.

## Intended use

The release supports:

- analysis of how coding agents approach paper reproduction;
- reconstruction of the 47 fixed task definitions;
- checking where evaluation code came from;
- rerunning a target evaluator when the required outputs are available; and
- building checked summary tables and visualizations.

Do not treat a log or a number found in a submitted file as proof of success.
The required experiment steps, submitted files, and reported number must each
be checked. An independent rerun of the checking program on saved outputs is
called a **replay**.
