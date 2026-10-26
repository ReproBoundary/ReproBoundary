#!/usr/bin/env bash
set -euo pipefail

mkdir -p artifacts/cable-checkpoints artifacts/cable-tensorboard logs
OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 python3 src/train_gpt.py \
  --model tiny \
  --pos-method cable \
  --dataset-dir data/wikitext-103 \
  --sequence-length 1024 \
  --num-epochs 1 \
  --total-batch-size 131072 \
  --batch-size 16 \
  --save-dir artifacts/cable-checkpoints/ \
  --writer-dir artifacts/cable-tensorboard \
  2>&1 | tee logs/cable-train-v4.log
