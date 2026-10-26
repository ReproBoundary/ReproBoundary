#!/usr/bin/env bash
set -euo pipefail

mkdir -p artifacts logs
PYTHONPATH=.:CIFAR python3 REDUCTION_PROTOCOL/run_sdot_v4.py \
  2>&1 | tee logs/solve_sdot.log
WANDB_MODE=offline PYTHONPATH=.:CIFAR python3 CIFAR/train_cifar10.py \
  --model=AlignFlow --seed=0 --wandb_name=AlignFlow_v4 \
  --total_steps=100001 --save_step=100000 \
  2>&1 | tee logs/train.log
bash REDUCTION_PROTOCOL/evaluate_alignflow_v4.sh
