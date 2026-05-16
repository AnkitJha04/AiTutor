from __future__ import annotations

import numpy as np

from backend.config.settings import get_settings
from backend.models.ollama_client import OllamaClient


class Embedder:
    def __init__(self) -> None:
        settings = get_settings()
        self.settings = settings
        self._model = None
        if settings.use_sentence_transformers:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(settings.embedding_model)
        else:
            self._client = OllamaClient(settings.ollama_base_url, settings.embedding_model)

    async def embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((1, 1), dtype="float32")
        if self.settings.use_sentence_transformers and self._model is not None:
            vectors = self._model.encode(texts, convert_to_numpy=True)
            return np.asarray(vectors, dtype="float32")
        embeddings = await self._client.embed(texts)
        return np.asarray(embeddings, dtype="float32")
