from __future__ import annotations

import hashlib
import re

import numpy as np

from backend.config.settings import get_settings


_HASH_DIM = 384
_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9\-']+")


class Embedder:
    def __init__(self) -> None:
        settings = get_settings()
        self.settings = settings
        self._model = None
        if settings.use_sentence_transformers:
            try:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(settings.embedding_model)
            except Exception:
                self._model = None

    def _hash_embed(self, text: str) -> np.ndarray:
        vector = np.zeros(_HASH_DIM, dtype="float32")
        for token in _TOKEN_RE.findall(text.lower()):
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            index = int.from_bytes(digest, "little") % _HASH_DIM
            vector[index] += 1.0
        norm = float(np.linalg.norm(vector))
        if norm > 0:
            vector /= norm
        return vector

    async def embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, _HASH_DIM), dtype="float32")
        if self.settings.use_sentence_transformers and self._model is not None:
            vectors = self._model.encode(texts, convert_to_numpy=True)
            return np.asarray(vectors, dtype="float32")
        embeddings = [self._hash_embed(text) for text in texts]
        return np.asarray(embeddings, dtype="float32")
