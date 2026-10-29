# Execution trajectories

This GitHub repository keeps only the trajectory index. The 423 compressed
`agent.log.gz` files are stored in the private
[Hugging Face dataset](https://huggingface.co/datasets/SupingSun/ReproBoundary-Execution-Trajectories)
at revision `57e17e11f795c6df9f7806ad2262fd32897ec2e6`.

[`TRAJECTORY_INDEX.csv`](TRAJECTORY_INDEX.csv) records the task, model-agent
setting, run state, dataset-relative path, source hash, released-file hash, and
redaction count for every planned run. Paths beginning with
`trajectories/runs/` are relative to the root of the Hugging Face dataset.

After downloading the dataset, run `python3 scripts/verify_dataset.py` from its
root. The script verifies all indexed paths and SHA-256 hashes, gzip
readability, release checksums, and configured sensitive-text patterns.

Leaderboard results are not stored in either the index or the trajectory
dataset.
