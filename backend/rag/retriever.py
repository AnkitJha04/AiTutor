from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from backend.database.vector_store import VectorStore
from backend.rag.embedder import Embedder


@dataclass
class RetrievedChunk:
    text: str
    score: float
    metadata: dict[str, str | int]


class Retriever:
    def __init__(self, store: VectorStore, embedder: Embedder) -> None:
        self.store = store
        self.embedder = embedder

    async def retrieve(
        self,
        query: str,
        top_k: int,
        candidate_k: int | None = None,
        chapter_title: str | None = None,
    ) -> list[RetrievedChunk]:
        if not query:
            return []
        candidate_k = candidate_k or top_k
        vectors = await self.embedder.embed([query])
        if isinstance(vectors, np.ndarray):
            query_vector = vectors[:1]
        else:
            query_vector = np.asarray(vectors[:1], dtype="float32")
        results = self.store.search(query_vector, candidate_k)

        filtered: list[tuple[float, dict[str, str | int]]] = []
        if chapter_title:
            chapter_lower = chapter_title.lower()
            for score, meta in results:
                chapter = str(meta.get("chapter", "")).lower()
                if chapter_lower in chapter:
                    filtered.append((score, meta))
        final_results = filtered if filtered else results

        chunks: list[RetrievedChunk] = []
        for score, meta in final_results[:top_k]:
            text = str(meta.get("text", ""))
            chunks.append(RetrievedChunk(text=text, score=score, metadata=meta))
        return chunks
