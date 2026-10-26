#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_ROOT="${PROJECT_ROOT}/data_external"
mkdir -p "${DATA_ROOT}"

check_md5() {
  local expected="$1" path="$2" actual
  if command -v md5sum >/dev/null 2>&1; then
    actual="$(md5sum "${path}" | awk '{print $1}')"
  else
    actual="$(md5 -q "${path}")"
  fi
  test "${actual}" = "${expected}" || {
    echo "MD5 mismatch for ${path}: ${actual}" >&2
    exit 41
  }
}

curl -L --fail --retry 5 \
  'https://zenodo.org/api/records/7992926/files/Processed_K50_dG_datasets.zip/content' \
  -o "${DATA_ROOT}/Processed_K50_dG_datasets.zip"
check_md5 f7e8c553efee734cf161ee6f2b0a09cf "${DATA_ROOT}/Processed_K50_dG_datasets.zip"
unzip -o "${DATA_ROOT}/Processed_K50_dG_datasets.zip" \
  'Processed_K50_dG_datasets/Tsuboyama2023_Dataset2_Dataset3_20230416.csv' \
  -d "${DATA_ROOT}"

curl -L --fail --retry 5 \
  'https://zenodo.org/api/records/7992926/files/AlphaFold_model_PDBs.zip/content' \
  -o "${DATA_ROOT}/AlphaFold_model_PDBs.zip"
check_md5 c29317a75f28d008b2718316995902ef "${DATA_ROOT}/AlphaFold_model_PDBs.zip"
unzip -o "${DATA_ROOT}/AlphaFold_model_PDBs.zip" -d "${DATA_ROOT}"

curl -L --fail --retry 5 \
  'https://life.bsc.es/pid/skempi2/database/download/SKEMPI2_PDBs.tgz' \
  -o "${DATA_ROOT}/SKEMPI2_PDBs.tgz"
mkdir -p "${DATA_ROOT}/SKEMPI2_PDBs"
tar -xzf "${DATA_ROOT}/SKEMPI2_PDBs.tgz" -C "${DATA_ROOT}/SKEMPI2_PDBs"
