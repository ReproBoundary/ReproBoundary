#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_ROOT="${1:-${PROJECT_ROOT}/artifacts/frozen_ta_bg_gmm}"
case "${OUTPUT_ROOT}" in
  "${PROJECT_ROOT}"/*) ;;
  *) echo "output must remain inside ${PROJECT_ROOT}" >&2; exit 2 ;;
esac

mkdir -p "${OUTPUT_ROOT}/pretrain_wandb" "${OUTPUT_ROOT}/anneal_wandb"

export WANDB_DIR="${OUTPUT_ROOT}/pretrain_wandb"
python3 "${PROJECT_ROOT}/REDUCTION_PROTOCOL/run_seeded_train.py" \
  -cd configs/paper/gmm -cn rev_kld_30 \
  training.max_iter=12500 \
  checkpointing.write_checkpoint_every=12500 \
  evaluation.eval_every=12500 \
  evaluation.big_eval_every=12500 \
  evaluation.NLL_every=12500 \
  evaluation.additional_sampling_eval_every=12500 \
  experiment.disable_wandb=false \
  experiment.wandb_offline=true \
  2>&1 | tee "${OUTPUT_ROOT}/pretrain.log"

PRETRAIN_CHECKPOINT="$(find "${OUTPUT_ROOT}/pretrain_wandb" -type f -name 'checkpoint_12499.pt' -print | LC_ALL=C sort | tail -n 1)"
test -n "${PRETRAIN_CHECKPOINT}"
test -s "${PRETRAIN_CHECKPOINT}"

export WANDB_DIR="${OUTPUT_ROOT}/anneal_wandb"
python3 "${PROJECT_ROOT}/REDUCTION_PROTOCOL/run_seeded_train.py" \
  -cd configs/paper/gmm -cn annealing_30 \
  training.checkpoint_path="${PRETRAIN_CHECKPOINT}" \
  training.training_mode.temp_sampling.iterations_per_step=5000 \
  training.training_mode.buffer.buffer_n_samples_per_T=500000 \
  training.training_mode.buffer.resample_to=500000 \
  training.max_iter=40000 \
  checkpointing.write_checkpoint_every=40000 \
  evaluation.eval_every=40000 \
  evaluation.big_eval_every=40000 \
  evaluation.NLL_every=40000 \
  evaluation.additional_sampling_eval_every=40000 \
  experiment.disable_wandb=false \
  experiment.wandb_offline=true \
  2>&1 | tee "${OUTPUT_ROOT}/anneal.log"

python3 "${PROJECT_ROOT}/REDUCTION_PROTOCOL/extract_metric.py" \
  "${OUTPUT_ROOT}/anneal.log" "${OUTPUT_ROOT}/metrics.json"
