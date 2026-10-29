# Contributing to ReproBoundary

This repository is an evidence record as well as a code repository. A change
must preserve the source and meaning of every task, trajectory index entry, and
score. Compressed execution logs are maintained in the separate Hugging Face
dataset rather than this GitHub repository.

## Changes we accept

- Documentation corrections and clearer explanations.
- Fixes to website display or support for keyboard and screen-reader users.
- Corrections to task descriptions with a public source.
- Fixes to a checking program that keep the same data, reported number, and
  calculation.
- Checked leaderboard data from a fixed set of runs.

## Evidence required for data changes

A change to a task, evaluator, or result must state:

1. which task or run changed;
2. why the old value was wrong;
3. the public source or saved evidence used for the correction;
4. the exact repository commit, file hash, or data version;
5. whether the change affects any reported number.

A **file hash** is a digital fingerprint that changes when file contents
change. A **repository commit** is an exact saved version of source code.

## Before opening a pull request

Run:

```bash
python3 scripts/build_site_data.py
python3 scripts/verify_release.py
```

The first command rebuilds the website task list from the main task table. The
second checks file hashes, indexes, counts, size limits, and common secret
patterns.

Do not include trajectory logs, datasets, trained model files, saved training
states, saved predictions, credentials, private machine paths, or complete
copies of other projects.
