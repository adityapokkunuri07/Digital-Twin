"""
Native 1536 Embedding Service — EmbeddingService implementation.

Uses OpenAI's text-embedding-3-small to produce native 1536-dimensional vectors
as required by the new architecture. 
Falls back to deterministic mock vectors when the API key is unavailable.
"""
import hashlib
from typing import List
import numpy as np
import logging

from backend.app.core.interfaces.embedding import EmbeddingService

logger = logging.getLogger(__name__)


class Native1536EmbeddingService(EmbeddingService):
    """
    OpenAI-backed embedding service producing 1536-dimensional vectors.
    Gracefully degrades to deterministic mock embeddings when API fails.
    """

    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self.dimension = 1536
        self.use_fallback = True

        if api_key:
            try:
                import openai
                self.client = openai.OpenAI(api_key=api_key)
                self.use_fallback = False
            except ImportError:
                logger.warning(
                    "openai package not installed. Falling back to mock 1536 embeddings."
                )
            except Exception as e:
                logger.warning(
                    f"OpenAI client failed to load: {e}. Falling back to mock embeddings."
                )

    def get_embedding(self, text: str) -> List[float]:
        if not text:
            return [0.0] * self.dimension

        if not self.use_fallback and hasattr(self, 'client'):
            try:
                response = self.client.embeddings.create(
                    input=text,
                    model="text-embedding-3-small",
                    dimensions=self.dimension
                )
                return response.data[0].embedding
            except Exception as e:
                logger.error(
                    f"OpenAI embedding error: {e}. Falling back to mock vector."
                )

        # Deterministic mock embedding
        seed = int(hashlib.md5(text.encode("utf-8")).hexdigest(), 16)
        rng = np.random.default_rng(seed)
        vec = rng.standard_normal(self.dimension)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    def get_dimension(self) -> int:
        return self.dimension
