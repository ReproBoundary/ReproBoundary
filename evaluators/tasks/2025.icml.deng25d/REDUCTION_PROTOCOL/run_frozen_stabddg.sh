#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_ROOT="${PROJECT_ROOT}/data_external"
ARTIFACT_ROOT="${PROJECT_ROOT}/artifacts"
LOG_ROOT="${PROJECT_ROOT}/logs"

cd "${PROJECT_ROOT}"
mkdir -p "${ARTIFACT_ROOT}/stability_finetuned" "${ARTIFACT_ROOT}/skempi_finetuned" \
  "${ARTIFACT_ROOT}/stabddg_eval" "${LOG_ROOT}"

test -f "${DATA_ROOT}/Processed_K50_dG_datasets/Tsuboyama2023_Dataset2_Dataset3_20230416.csv"
test -d "${DATA_ROOT}/AlphaFold_model_PDBs"
test -d "${DATA_ROOT}/SKEMPI2_PDBs/PDBs"

python3 stability_finetune.py \
  --checkpoint model_ckpts/proteinmpnn.pt \
  --pdb_dir "${DATA_ROOT}/AlphaFold_model_PDBs" \
  --stability_data "${DATA_ROOT}/Processed_K50_dG_datasets/Tsuboyama2023_Dataset2_Dataset3_20230416.csv" \
  --num_epochs 70 --batch_size 25000 --lr 3e-5 --seed 0 \
  --run_name stability_full --model_save_dir "${ARTIFACT_ROOT}/stability_finetuned" \
  2>&1 | tee "${LOG_ROOT}/stability_finetune.log"

test -s "${ARTIFACT_ROOT}/stability_finetuned/stability_full_final.pt"

python3 skempi_finetune.py \
  --checkpoint "${ARTIFACT_ROOT}/stability_finetuned/stability_full_final.pt" \
  --skempi_pdb_dir "${DATA_ROOT}/SKEMPI2_PDBs/PDBs" \
  --skempi_path data/SKEMPI/filtered_skempi.csv \
  --train_split_path data/SKEMPI/train_pdb.pkl \
  --epochs 200 --batch_size 25000 --lr 1e-6 --seed 0 \
  --run_name skempi_full --model_save_dir "${ARTIFACT_ROOT}/skempi_finetuned" \
  2>&1 | tee "${LOG_ROOT}/skempi_finetune.log"

if grep -Fq "Failed on complex" "${LOG_ROOT}/skempi_finetune.log"; then
  echo "binding fine-tuning silently skipped at least one required interface" >&2
  exit 42
fi
test -s "${ARTIFACT_ROOT}/skempi_finetuned/skempi_full_final.pt"

python3 skempi_eval.py \
  --checkpoint "${ARTIFACT_ROOT}/skempi_finetuned/skempi_full_final.pt" \
  --skempi_pdb_dir "${DATA_ROOT}/SKEMPI2_PDBs/PDBs" \
  --skempi_path data/SKEMPI/filtered_skempi.csv \
  --skempi_split_path data/SKEMPI/test_pdb.pkl \
  --ensemble 20 --batch_size 10000 --seed 0 \
  --run_name stabddg_eval --output_dir "${ARTIFACT_ROOT}/stabddg_eval" \
  2>&1 | tee "${LOG_ROOT}/skempi_eval.log"

python3 REDUCTION_PROTOCOL/extract_metric.py \
  --predictions "${ARTIFACT_ROOT}/stabddg_eval/stabddg_eval.csv" \
  --target-manifest REDUCTION_PROTOCOL/skempi_test_ids.jsonl \
  --output "${ARTIFACT_ROOT}/stabddg_eval/metrics.json" \
  2>&1 | tee "${LOG_ROOT}/metric.log"

shasum -a 256 \
  "${ARTIFACT_ROOT}/stability_finetuned/stability_full_final.pt" \
  "${ARTIFACT_ROOT}/skempi_finetuned/skempi_full_final.pt" \
  "${ARTIFACT_ROOT}/stabddg_eval/stabddg_eval.csv" \
  "${ARTIFACT_ROOT}/stabddg_eval/metrics.json" \
  > "${ARTIFACT_ROOT}/SHA256SUMS"
