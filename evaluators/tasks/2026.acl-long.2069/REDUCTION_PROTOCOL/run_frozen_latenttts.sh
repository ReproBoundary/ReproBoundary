#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
test "$(shasum -a 256 data/gsm_test.json | awk '{print $1}')" = "46ce5b0c44fde0bfc8cf1e7492aa640b96111d9dcb80a54340d9911141a9caa9"
test -f checkpoints/coconut/config.json
exec python3 REDUCTION_PROTOCOL/run_frozen_latenttts.py
