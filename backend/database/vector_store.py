from __future__ import annotations

import pickle
from dataclasses import dataclass
from pathlib import Path

import faiss
import numpy as np


@dataclass
class VectorIndex:
    index: faiss.Index
    metadata: list[dict[str, str | int]]


class VectorStore:
    def __init__(self, dim: int) -> None:
        self.index = faiss.IndexFlatIP(dim)
        self.metadata: list[dict[str, str | int]] = []

    def add(self, vectors: np.ndarray, metadatas: list[dict[str, str | int]]) -> None:
        faiss.normalize_L2(vectors)
        self.index.add(vectors)
        self.metadata.extend(metadatas)

    def search(self, query_vector: np.ndarray, top_k: int) -> list[tuple[float, dict[str, str | int]]]:
        faiss.normalize_L2(query_vector)
        scores, indices = self.index.search(query_vector, top_k)
        results: list[tuple[float, dict[str, str | int]]] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            results.append((float(score), self.metadata[idx]))
        return results

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(path.with_suffix(".faiss")))
        with path.with_suffix(".meta.pkl").open("wb") as handle:
            pickle.dump(self.metadata, handle)

    @classmethod
    def load(cls, path: Path) -> "VectorStore":
        index = faiss.read_index(str(path.with_suffix(".faiss")))
        with path.with_suffix(".meta.pkl").open("rb") as handle:
            metadata = pickle.load(handle)
        store = cls(index.d)
        store.index = index
        store.metadata = metadata
        return store
