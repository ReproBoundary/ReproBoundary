#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "$0")/.." && pwd)"
checkpoint_path="${ROBUST_CONFORMAL_CHECKPOINT:?set ROBUST_CONFORMAL_CHECKPOINT to the pinned OpenOOD CIFAR-10 ResNet-18 v1.5 checkpoint}"
artifact_root="${ARTIFACT_ROOT:-$project_root/artifacts/frozen_table6}"
score_root="$artifact_root/datasets_scores/cifar10_texture/n_train_2000_0.03"
score_path="$score_root/cifar10/resnet18_32x32/react"

cd "$project_root"
python ImageOD/score_datasets.py \
  --save_path "$score_root" \
  --id_dataset cifar10 \
  --ood_dataset texture \
  --postprocess react \
  --net_ckpt_path "$checkpoint_path" \
  --net resnet18_32x32 \
  --p_train 0.03 \
  --n_train 2000

python main.py \
  --full_save_path \
  --local \
  --no_distribute \
  --save_path "$artifact_root/statistical_run" \
  --seed 42 \
  --n_seeds 100 \
  --initial_labeled 50 \
  --n_cal 3000 \
  --p_cal 0.03 \
  --n_test 1000 \
  --p_test 0.05 \
  --level 0.01 \
  --dataset scores_cifar10 \
  --dataset_path "$score_path" \
  --outlr_dataset texture

python REDUCTION_PROTOCOL/serialize_metric.py \
  "$artifact_root/statistical_run/results/results.pkl" \
  "$artifact_root/metrics.json"
