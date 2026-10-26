#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path


EXPECTED_TASK_DIRS = (
    "IconQA", "flickr30k", "grounding", "ScienceQA",
    "OCRVQA", "ImageNet", "vizwiz", "VQAv2",
)
EXPECTED_QUESTION_SHA256 = "e533e0df037b74d328a2c25b3b2474778880fa8c22132cdcf168092c0eb59c4e"
EXPECTED_SPLIT_SHA256 = "85c7820b9f136e572579a01dab2c77a7f8140b59211e421fa5182491d45ee3a7"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lora-root", type=Path, required=True)
    parser.add_argument("--model-root", type=Path, required=True)
    parser.add_argument("--datasets-root", type=Path, required=True)
    parser.add_argument("--question-file", type=Path, required=True)
    args = parser.parse_args()

    assert (args.model_root / "config.json").is_file()
    for task_dir in EXPECTED_TASK_DIRS:
        root = args.lora_root / task_dir
        for filename in ("adapter_config.json", "adapter_model.bin", "non_lora_trainables.bin"):
            assert (root / filename).is_file(), f"missing {root / filename}"

    scienceqa_root = args.datasets_root / "ScienceQA"
    split_path = scienceqa_root / "pid_splits.json"
    problems_path = scienceqa_root / "problems.json"
    assert split_path.is_file() and problems_path.is_file()
    assert sha256(split_path) == EXPECTED_SPLIT_SHA256
    assert sha256(args.question_file) == EXPECTED_QUESTION_SHA256

    split_ids = [str(value) for value in json.loads(split_path.read_text())["test"]]
    problems = json.loads(problems_path.read_text())
    questions = json.loads(args.question_file.read_text())
    question_ids = [str(row["question_id"]) for row in questions]
    assert len(split_ids) == len(set(split_ids)) == 4241
    assert len(question_ids) == len(set(question_ids)) == 4241
    assert set(question_ids) == set(split_ids)
    assert all(question_id in problems for question_id in question_ids)

    options = "ABCDE"
    for row in questions:
        question_id = str(row["question_id"])
        assert row["answer"] == options[problems[question_id]["answer"]]
        if "image" in row:
            assert (args.datasets_root / row["image"]).is_file(), f"missing image for {question_id}"

    print(json.dumps({
        "status": "PASS",
        "test_count": len(question_ids),
        "question_sha256": EXPECTED_QUESTION_SHA256,
        "split_sha256": EXPECTED_SPLIT_SHA256,
        "lora_task_count": len(EXPECTED_TASK_DIRS),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
