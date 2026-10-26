#!/usr/bin/env bash
set -euo pipefail

mkdir -p artifacts/city-map logs
PYTHONPATH=. python3 -m value_coding_features.city_map_pipeline \
  --epochs 10 \
  --train-pairs 70000 \
  --val-pairs 175000 \
  --batch-size 1024 \
  --eval-batch-size 4096 \
  --seed 42 \
  --device cuda \
  --output-dir artifacts/city-map \
  2>&1 | tee logs/city-map-v4.log
python3 REDUCTION_PROTOCOL/extract_city_map_metric.py \
  logs/city-map-v4.log artifacts/city-map-baseline-accuracy.json
