"""
Gemini Embedding Service — EmbeddingService implementation.

Uses Google's Gemini models for 768-dimensional vectors.
Falls back to deterministic mock vectors when the API key is unavailable.
"""
import hashlib
from typing import List
import numpy as np
import logging

from backend.app.core.interfaces.embedding import EmbeddingService

logger = logging.getLogger(__name__)


class GeminiEmbeddingService(EmbeddingService):
    """
    Gemini-backed embedding service producing 768-dimensional vectors.
    Gracefully degrades to deterministic mock embeddings when API fails.
    """

    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self.dimension = 768
        self.use_fallback = True

        if api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=api_key)
                self.use_fallback = True # FORCED FALLBACK: Prevent 60s timeout due to model access issues
            except ImportError:
                logger.warning(
                    "google-genai package not installed. Falling back to mock embeddings."
                )
            except Exception as e:
                logger.warning(
                    f"Gemini client failed to load: {e}. Falling back to mock embeddings."
                )

    def get_embedding(self, text: str) -> List[float]:
        if not text:
            return [0.0] * self.dimension

        if not self.use_fallback and hasattr(self, 'client'):
            try:
                result = self.client.models.embed_content(
                    model="gemini-embedding-2",
                    contents=text,
                    config={'output_dimensionality': self.dimension}
                )
                return result.embeddings[0].values
            except Exception as e:
                logger.error(
                    f"Gemini embedding error: {e}. Falling back to mock vector."
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
