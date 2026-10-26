#!/usr/bin/env bash
set -euo pipefail

mkdir -p artifacts logs
python3 REDUCTION_PROTOCOL/prepare_fid_v4.py
PYTHONPATH=.:CIFAR torchrun --nproc-per-node=1 artifacts/compute_fid_dopri5_v4.py \
  2>&1 | tee logs/evaluate.log
python3 REDUCTION_PROTOCOL/extract_alignflow_fid.py \
  artifacts/alignflow-cifar10-fid50k.csv artifacts/alignflow-cifar10-fid50k.json
