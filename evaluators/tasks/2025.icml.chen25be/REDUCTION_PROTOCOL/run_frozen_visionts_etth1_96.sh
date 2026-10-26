#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_FILE="$PROJECT_ROOT/long_term_tsf/dataset/ETT-small/ETTh1.csv"
CHECKPOINT_FILE="$PROJECT_ROOT/ckpt/mae_visualize_vit_base.pth"
ARTIFACT_DIR="$PROJECT_ROOT/artifacts/visionts_etth1_96"

if [[ ! -f "$DATA_FILE" ]]; then
  echo "Missing frozen ETTh1.csv; see REDUCTION_PROTOCOL/SOURCE_BINDINGS.json" >&2
  exit 2
fi
if [[ ! -f "$CHECKPOINT_FILE" ]]; then
  echo "Missing frozen MAE ViT-Base checkpoint; see REDUCTION_PROTOCOL/SOURCE_BINDINGS.json" >&2
  exit 2
fi

python3 - "$DATA_FILE" "$CHECKPOINT_FILE" <<'PY'
import hashlib
import os
import sys

data_path, checkpoint_path = sys.argv[1:]
with open(data_path, "rb") as handle:
    payload = handle.read()
git_blob = hashlib.sha1(b"blob " + str(len(payload)).encode() + b"\0" + payload).hexdigest()
if git_blob != "a52c4925778c07c1ef1a2cf6fd01594919717d9e":
    raise SystemExit(f"ETTh1 git-blob identity mismatch: {git_blob}")
if len(payload.splitlines()) != 17421:
    raise SystemExit("ETTh1 row-count mismatch")
if os.path.getsize(checkpoint_path) != 447725789:
    raise SystemExit("MAE ViT-Base checkpoint size mismatch")
PY

mkdir -p "$ARTIFACT_DIR"
cd "$PROJECT_ROOT/long_term_tsf"
python3 -u run.py \
  --task_name long_term_forecast \
  --is_training 1 \
  --model VisionTS \
  --root_path "$PROJECT_ROOT/long_term_tsf/dataset/ETT-small/" \
  --data_path ETTh1.csv \
  --save_dir "$ARTIFACT_DIR" \
  --model_id VisionTS_ETTh1_96 \
  --data ETTh1 \
  --features M \
  --train_epochs 0 \
  --batch_size 32 \
  --num_workers 8 \
  --vm_arch mae_base \
  --vm_ckpt "$PROJECT_ROOT/ckpt/" \
  --seq_len 2880 \
  --periodicity 24 \
  --pred_len 96 \
  --norm_const 0.4 \
  --align_const 0.4 \
  2>&1 | tee "$ARTIFACT_DIR/run.log"

python3 "$PROJECT_ROOT/REDUCTION_PROTOCOL/extract_metric.py" \
  --metrics "$ARTIFACT_DIR/results/_/metrics.npy" \
  --predictions "$ARTIFACT_DIR/results/_/pred.npy" \
  --labels "$ARTIFACT_DIR/results/_/true.npy" \
  --output "$ARTIFACT_DIR/metrics.json"
