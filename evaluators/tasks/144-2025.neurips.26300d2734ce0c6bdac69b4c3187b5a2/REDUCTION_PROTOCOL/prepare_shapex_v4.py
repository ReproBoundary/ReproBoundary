#!/usr/bin/env python3
"""Download frozen ShapeX assets and repair audited release path/split defects."""

import hashlib
import json
from pathlib import Path

from huggingface_hub import snapshot_download


snapshot_download(
    repo_id="bosonhwang/ShapeX", repo_type="dataset", local_dir=".",
    allow_patterns=["datasets/mcce.pt", "datasets/split=301.pt", "checkpoints/classification_models/mcce_transformer.pt"],
)
dataset_candidates = [Path("datasets/mcce.pt"), Path("datasets/split=301.pt")]
if not any(path.is_file() for path in dataset_candidates):
    raise SystemExit("the ShapeX release did not contain the MCC-E tensor")
classifier = Path("checkpoints/classification_models/mcce_transformer.pt")
if not classifier.is_file():
    raise SystemExit("the ShapeX release did not contain the MCC-E Transformer checkpoint")

source = Path("exp_saliency_general.py")
text = source.read_text(encoding="utf-8")
text = text.replace(
    'ds_cfg_path = f"/home/gbsguest/Research/boson/TS/XTS/ShapeX-beta/configs/{dataset_name}.yaml"',
    'ds_cfg_path = os.path.join(config.base.root_dir, "configs", f"{dataset_name}.yaml")',
    1,
)
text = text.replace(
    'data_dict={ # \n            "TEST":train_dataset,\n            "VAL":val_dataset,\n            "TRAIN":test_dataset\n        }',
    'data_dict={\n            "TRAIN":train_dataset,\n            "VAL":val_dataset,\n            "TEST":test_dataset\n        }',
)
text = text.replace("n_classes = 4,", "n_classes = self.args.num_classes,", 1)
required = (
    'os.path.join(config.base.root_dir, "configs"',
    '"TRAIN":train_dataset',
    "n_classes = self.args.num_classes",
)
if any(item not in text for item in required):
    raise SystemExit("ShapeX sources did not match the audited release")
source.write_text(text, encoding="utf-8")

payload = {
    "fixes": [
        "resolve dataset YAML under the checked-out repository",
        "restore TRAIN/VAL/TEST dataset mapping",
        "use the paper's two-class MCC-E classifier output",
    ],
    "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    "classifier_sha256": hashlib.sha256(classifier.read_bytes()).hexdigest(),
    "dataset_files": [str(path) for path in dataset_candidates if path.is_file()],
}
output = Path("artifacts/shapex-release-fixes.json")
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
print(json.dumps(payload, indent=2))
