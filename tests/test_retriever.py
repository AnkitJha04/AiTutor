import numpy as np
import pytest

from backend.database.vector_store import VectorStore
from backend.rag.embedder import Embedder
from backend.rag.retriever import Retriever


class DummyEmbedder(Embedder):
    async def embed(self, texts):
        return np.array([[1.0, 0.0, 0.0]], dtype="float32")


@pytest.mark.asyncio
async def test_retriever_returns_chunks():
    store = VectorStore(dim=3)
    vectors = np.array([[1.0, 0.0, 0.0]], dtype="float32")
    store.add(vectors, [{"text": "sample", "page": 1}])
    retriever = Retriever(store, DummyEmbedder())
    chunks = await retriever.retrieve("sample", 1)
    assert chunks
