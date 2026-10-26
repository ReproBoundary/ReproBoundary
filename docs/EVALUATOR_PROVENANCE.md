# Where the evaluator files came from

An **evaluator** is the program that calculates a task's target metric from
saved outputs. This file explains which evaluator files come from source-paper
repositories and which files were written for ReproBoundary.

## How evaluator versions are fixed

Every task records:

- a public evaluator source URL;
- an exact Git commit ID;
- an evaluation contract named `TARGET_EVALUATION.json`; and
- a SHA-256 hash for that contract.

A **commit ID** names one exact version of a Git repository. A **SHA-256 hash**
is a digital fingerprint used to detect a changed file. Fixing both values
prevents a later repository update from silently changing the benchmark.

The source URL does not mean that every file in this release was copied from
the source-paper repository. ReproBoundary also uses **helper files**, which are
small scripts or configurations that prepare inputs, check completeness, call
an evaluator, convert file formats, or combine repeated scores.

## Summary

- 46 of 47 evaluator URLs use the same GitHub repository recorded for the
  corresponding task.
- The former `luotianze666/SoFlow` URL now redirects to
  `zlab-princeton/SoFlow`. This was a repository move, not a change of
  evaluator. Both URLs point to the same fixed commit and file contents.
- The LinearPatch task uses EleutherAI's `lm-evaluation-harness`. This is an
  external evaluation package named by the source paper and source code.
- Eleven tasks call an original repository program directly.
- Thirty-five tasks call a `REDUCTION_PROTOCOL` helper included in this
  release.
- Task 019 calls a wrapper written for ReproBoundary outside the source-paper
  repository.

`REDUCTION_PROTOCOL` is the directory name for helper files that implement the
fixed, resource-bounded task instructions. A **resource-bounded task** reduces
training, search, or repeated work to fit the benchmark limit while keeping the
complete final evaluation set.

Do not describe a helper as source-paper code unless its `NOTICE.md` file says
that it was copied from that source.

## SoFlow

The two SoFlow URLs resolve commit
`cc47661a0b0843f8f1b6cff3a17107a052d18b21` to the same repository tree. A
**repository tree** is the complete set of files stored by one commit. The two
URLs also resolve `evaluator.py` to the same Git file object.

The fixed evaluator uses the source repository's code and CIFAR-10 reference
file to calculate FID-50K. **FID**, or Frechet Inception Distance, compares the
feature distributions of generated and reference images. `50K` means that the
calculation uses 50,000 generated images.

## LinearPatch

The LinearPatch paper, repository README, dependency file, and
`main_distill.py` all name `lm-evaluation-harness` version 0.4.4. The source
code evaluates zero-shot ARC-Easy accuracy. **Zero-shot** means that no worked
example is placed in the model prompt. **ARC-Easy** is a multiple-choice science
question dataset.

The fixed ReproBoundary task keeps:

- the original prompt format;
- the mapping from each question to its correct answer;
- the answer-choice order;
- all 2,376 test questions; and
- raw accuracy, which is the number of correct answers divided by the number
  of questions.

The helper changes only the task name and the local path used to load a
hash-checked copy of the dataset.

## What these checks show

The records above show that the evaluator sources and versions match the task
definitions. They also show that the helper files keep the stated data and
metric rules.

They do not show that two separate implementations always produce the same
number. That claim would require a **regression test**, meaning a test that runs
both implementations on the same fixed inputs and compares every output.

Before claiming separate numerical validation, add:

1. a test that compares the SoFlow FID result with another standard FID
   implementation on the same saved image features; and
2. a test that compares the original ARC-Easy evaluator with the fixed
   ReproBoundary evaluator, checking every answer and the final accuracy.
