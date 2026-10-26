#!/usr/bin/env bash
set -euo pipefail

mkdir -p artifacts logs checkpoints/explainer
OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 python3 REDUCTION_PROTOCOL/run_shapex_v4.py \
  2>&1 | tee logs/shapex-v4.log
python3 REDUCTION_PROTOCOL/extract_shapex_metric.py \
  results.txt artifacts/shapex-mcce-auprc.json
