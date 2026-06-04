"""
Local Transformer Embedding Service — EmbeddingService implementation.

Uses SentenceTransformers (all-MiniLM-L6-v2) for local, zero-cost vector generation.
Falls back to deterministic MD5-seeded mock vectors when the model is unavailable.
"""
import os
import hashlib
from typing import List
import numpy as np
import logging

from backend.app.core.interfaces.embedding import EmbeddingService

logger = logging.getLogger(__name__)


class LocalTransformerEmbeddingService(EmbeddingService):
    """
    Local SentenceTransformer embedding service producing 384-dimensional vectors.
    Gracefully degrades to deterministic mock embeddings when the model can't load.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = None
        self.dimension = 384
        self.use_fallback = True

        # Skip model loading if mock mode is explicitly set
        if os.getenv("MOCK_EMBEDDINGS", "false").lower() != "true":
            try:
                from sentence_transformers import SentenceTransformer
                self.model = SentenceTransformer(model_name)
                self.use_fallback = False
                logger.info(f"SentenceTransformer '{model_name}' loaded successfully.")
            except Exception as e:
                logger.warning(
                    f"Could not load SentenceTransformer: {e}. "
                    "Using deterministic mock embeddings."
                )

    def get_embedding(self, text: str) -> List[float]:
        if not text:
            return [0.0] * self.dimension

        if not self.use_fallback and self.model:
            try:
                emb = self.model.encode(text)
                return emb.tolist()
            except Exception as e:
                logger.error(
                    f"Error encoding embedding: {e}. Falling back to mock vector."
                )

        # Deterministic mock embedding based on MD5 hashing
        seed = int(hashlib.md5(text.encode("utf-8")).hexdigest(), 16)
        rng = np.random.default_rng(seed)
        vec = rng.standard_normal(self.dimension)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    def get_dimension(self) -> int:
        return self.dimension
