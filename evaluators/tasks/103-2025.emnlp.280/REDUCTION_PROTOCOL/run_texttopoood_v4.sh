#!/usr/bin/env bash
set -euo pipefail

repo_root=$(pwd)
mkdir -p artifacts logs

(
  cd tntood
  python3 main.py \
    --datasets cora \
    --shift_type feature \
    --noise_level 0.9 \
    --num_layers 2 \
    --learning_rate 0.0001 \
    --dropout 0.3 \
    --use_tntood \
    --runs 1 \
    --seed 42
) 2>&1 | tee logs/evaluate.log

python3 REDUCTION_PROTOCOL/extract_texttopoood_metric.py \
  --results-root tntood/results \
  --output artifacts/texttopoood-cora-feature-0p90-auroc.json

test -s "$repo_root/artifacts/texttopoood-cora-feature-0p90-auroc.json"
