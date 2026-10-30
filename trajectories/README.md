# Execution trajectories

This GitHub repository keeps only the trajectory index. The 423 compressed
`agent.log.gz` files are stored in the private
[Hugging Face dataset](https://huggingface.co/datasets/SupingSun/ReproBoundary-Execution-Trajectories)
at revision `57e17e11f795c6df9f7806ad2262fd32897ec2e6`.

[`TRAJECTORY_INDEX.csv`](TRAJECTORY_INDEX.csv) records the task, model-agent
setting, run state, dataset-relative path, source hash, released-file hash, and
redaction count for every planned run. Paths beginning with
`trajectories/runs/` are relative to the root of the Hugging Face dataset.

Follow the complete installation, authentication, and fixed-revision download
commands in the [main README](../README.md). The two verification commands run
from different directories:

```bash
# From the GitHub repository root:
python3 scripts/verify_release.py

# From the downloaded Hugging Face dataset root:
python3 scripts/verify_dataset.py
```

The dataset check verifies all indexed paths and SHA-256 hashes, gzip
readability, release checksums, and configured sensitive-text patterns.

## Inspect one log

Run this from the downloaded Hugging Face dataset root. It uses the first row
of the index, checks the file fingerprint, and prints no more than 20 lines.

```bash
python3 - <<'PY'
import csv
import gzip
import hashlib
import itertools
from pathlib import Path

root = Path(".")
with (root / "trajectories/TRAJECTORY_INDEX.csv").open(encoding="utf-8") as f:
    row = next(csv.DictReader(f))

log = root / row["trajectory_path"]
digest = hashlib.sha256()
with log.open("rb") as f:
    for block in iter(lambda: f.read(1024 * 1024), b""):
        digest.update(block)

print("task:", row["task_id"])
print("state:", row["state_status"])
print("path:", log)
print("sha256 matches index:", digest.hexdigest() == row["released_log_sha256"])
print("first 20 lines:")
with gzip.open(log, "rt", encoding="utf-8", errors="replace") as f:
    for line in itertools.islice(f, 20):
        print(line.rstrip())
PY
```

This is a release-integrity and log-reading check, not a replay of the task's
scientific metric. The trajectory dataset does not include saved predictions,
checkpoints, model weights, or training states required by many evaluators.

Leaderboard results are not stored in either the index or the trajectory
dataset.
