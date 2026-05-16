import numpy as np

from backend.database.vector_store import VectorStore


def test_vector_store_roundtrip(tmp_path):
    store = VectorStore(dim=3)
    vectors = np.array([[1.0, 0.0, 0.0]], dtype="float32")
    store.add(vectors, [{"text": "sample"}])
    path = tmp_path / "index"
    store.save(path)
    loaded = VectorStore.load(path)
    results = loaded.search(np.array([[1.0, 0.0, 0.0]], dtype="float32"), 1)
    assert results
