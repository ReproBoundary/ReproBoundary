#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
artifact_root="${PLSTM_ARTIFACT_ROOT:-${project_root}/artifacts/frozen_seed42}"
mkdir -p "${artifact_root}"

export LOGLEVEL=INFO
export OUTPUT_DIR="${artifact_root}"
export WANDB_MODE=disabled

cd "${project_root}"
PYTHONPATH=. python3 scripts/run_experiment_simplified.py \
  --use_nnx \
  --metrics_output "${artifact_root}/metrics.json" \
  --config_name experiments/spl/arrow_pointing_extrapolation_plstm \
  optimizer.learning_rate.peak_value=0.0001 \
  aux.seed=42 \
  trainer.model_seed=43 \
  trainer.mixup_seed=44 \
  trainer.dropout_seed=45 \
  trainer.logging=false

python3 - "${artifact_root}/metrics.json" <<'PY'
import json
import math
import sys

path = sys.argv[1]
data = json.load(open(path, encoding="utf-8"))
value = data.get("test_ext/acc1")
if not isinstance(value, (int, float)) or not math.isfinite(value) or not 0.0 <= value <= 1.0:
    raise SystemExit("missing or invalid test_ext/acc1")
print(json.dumps({"metric_id": "arrow_pointing_ext_test_accuracy", "value": value}, sort_keys=True))
PY
