#!/usr/bin/env python3
"""Materialize BEIR SciFact and ordered Qwen-Embedding-0.6B vectors."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import torch
from beir import util
from beir.datasets.data_loader import GenericDataLoader
from sentence_transformers import SentenceTransformer


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def encode(model: SentenceTransformer, texts: list[str], prompt_name: str | None = None) -> torch.Tensor:
    kwargs = {
        "batch_size": 16, "show_progress_bar": True,
        "convert_to_tensor": True, "normalize_embeddings": True,
    }
    if prompt_name is not None:
        kwargs["prompt_name"] = prompt_name
    return model.encode(texts, **kwargs).cpu()


def main() -> None:
    data_root = Path("data/beir")
    dataset_dir = data_root / "scifact"
    if not dataset_dir.is_dir():
        util.download_and_unzip(
            "https://public.ukp.informatik.tu-darmstadt.de/thakur/BEIR/datasets/scifact.zip",
            str(data_root),
        )
    corpus_train, queries_train, _ = GenericDataLoader(str(dataset_dir)).load(split="train")
    corpus_test, queries_test, _ = GenericDataLoader(str(dataset_dir)).load(split="test")
    if list(corpus_train) != list(corpus_test):
        raise SystemExit("SciFact train and test corpus ID orders differ")
    corpus_ids = sorted(
        corpus_test,
        key=lambda key: len(corpus_test[key].get("title", "") + corpus_test[key].get("text", "")),
        reverse=True,
    )
    corpus_texts = [
        (corpus_test[key].get("title", "") + " " + corpus_test[key].get("text", "")).strip()
        for key in corpus_ids
    ]
    train_ids, test_ids = list(queries_train), list(queries_test)
    model = SentenceTransformer("Qwen/Qwen3-Embedding-0.6B", trust_remote_code=True)
    destination = Path("data/embeddings/qwen-0.6b/scifact")
    for split, ids, queries in (
        ("train", train_ids, queries_train), ("test", test_ids, queries_test),
    ):
        path = destination / split / "queries_embeddings.pt"
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(encode(model, [queries[key] for key in ids], "query"), path)
    corpus_path = destination / "test/corpus_embeddings.pt"
    torch.save(encode(model, corpus_texts), corpus_path)

    payload = {
        "embedding_model": "Qwen/Qwen3-Embedding-0.6B",
        "normalization": "L2 row normalization",
        "train_query_count": len(train_ids), "test_query_count": len(test_ids),
        "corpus_count": len(corpus_ids),
        "train_query_ids_sha256": hashlib.sha256("\n".join(train_ids).encode()).hexdigest(),
        "test_query_ids_sha256": hashlib.sha256("\n".join(test_ids).encode()).hexdigest(),
        "corpus_ids_sha256": hashlib.sha256("\n".join(corpus_ids).encode()).hexdigest(),
        "embedding_files": {
            str(path): digest(path)
            for path in sorted(destination.rglob("*.pt"))
        },
    }
    output = Path("artifacts/scifact-embedding-manifest.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
