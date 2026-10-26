#!/usr/bin/env bash
set -euo pipefail

mkdir -p artifacts logs
python3 REDUCTION_PROTOCOL/prepare_ider_cifar10.py 2>&1 | tee logs/prepare.log
python3 main.py \
  --model ider --dataset seq-cifar10 --device cuda:0 --seed 0 --n_tasks 5 \
  --buffer_size 200 --lr 0.03 --minibatch_size 32 --batch_size 32 --n_epochs 5 \
  --weighta 0.05 --weightb 0.05 --weightc 0.5 --weightmask 1.0 \
  --class_balance true --disable_log 1 --ignore_other_metrics 1 --non_verbose 1 \
  --savecheckpoint false --run_name ider-v4 \
  2>&1 | tee artifacts/ider-run.log
python3 REDUCTION_PROTOCOL/extract_ider_metric.py artifacts/ider-run.log METRICS.json
