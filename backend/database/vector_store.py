from __future__ import annotations

import pickle
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class VectorIndex:
    vectors: np.ndarray
    metadata: list[dict[str, str | int]]


class VectorStore:
    def __init__(self, dim: int) -> None:
        self.dim = dim
        self.vectors = np.empty((0, dim), dtype="float32")
        self.metadata: list[dict[str, str | int]] = []

    def _normalize(self, vectors: np.ndarray) -> np.ndarray:
        if vectors.ndim == 1:
            vectors = vectors.reshape(1, -1)
        if vectors.size == 0:
            return vectors.astype("float32")
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return (vectors / norms).astype("float32")

    def add(self, vectors: np.ndarray, metadatas: list[dict[str, str | int]]) -> None:
        normalized = self._normalize(np.asarray(vectors, dtype="float32"))
        if normalized.size == 0:
            return
        if normalized.shape[1] != self.dim:
            raise ValueError("Vector dimension mismatch")
        self.vectors = np.vstack([self.vectors, normalized])
        self.metadata.extend(metadatas)

    def search(self, query_vector: np.ndarray, top_k: int) -> list[tuple[float, dict[str, str | int]]]:
        if self.vectors.size == 0 or top_k <= 0:
            return []
        normalized_query = self._normalize(np.asarray(query_vector, dtype="float32"))
        if normalized_query.size == 0:
            return []
        scores = self.vectors @ normalized_query[0]
        order = np.argsort(scores)[::-1][:top_k]
        results: list[tuple[float, dict[str, str | int]]] = []
        for idx in order:
            results.append((float(scores[idx]), self.metadata[int(idx)]))
        return results

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "dim": self.dim,
            "vectors": self.vectors,
            "metadata": self.metadata,
        }
        with path.with_suffix(".pkl").open("wb") as handle:
            pickle.dump(payload, handle)

    @classmethod
    def load(cls, path: Path) -> "VectorStore":
        with path.with_suffix(".pkl").open("rb") as handle:
            payload = pickle.load(handle)
        store = cls(int(payload["dim"]))
        store.vectors = np.asarray(payload["vectors"], dtype="float32")
        store.metadata = list(payload["metadata"])
        return store
