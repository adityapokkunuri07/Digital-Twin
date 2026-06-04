import os
from abc import ABC, abstractmethod
from typing import List
import hashlib
import numpy as np
import logging

logger = logging.getLogger(__name__)

class EmbeddingService(ABC):
    @abstractmethod
    def get_embedding(self, text: str) -> List[float]:
        pass

    @abstractmethod
    def get_dimension(self) -> int:
        pass


class LocalTransformerEmbeddingService(EmbeddingService):
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = None
        self.dimension = 384
        self.use_fallback = True

        # Skip model loading if mock mode is explicitly set to avoid HuggingFace model download timeouts offline
        if os.getenv("MOCK_EMBEDDINGS", "false").lower() != "true":
            try:
                from sentence_transformers import SentenceTransformer
                self.model = SentenceTransformer(model_name)
                self.use_fallback = False
                logger.info(f"SentenceTransformer '{model_name}' loaded successfully.")
            except Exception as e:
                logger.warning(f"Could not load SentenceTransformer: {e}. Using deterministic mock embeddings.")

    def get_embedding(self, text: str) -> List[float]:
        if not text:
            return [0.0] * self.dimension

        if not self.use_fallback and self.model:
            try:
                emb = self.model.encode(text)
                return emb.tolist()
            except Exception as e:
                logger.error(f"Error encoding embedding: {e}. Falling back to mock vector.")

        # Deterministic mock embedding based on MD5 hashing
        # Generate 384 floats using hash chunks
        seed = int(hashlib.md5(text.encode("utf-8")).hexdigest(), 16)
        rng = np.random.default_rng(seed)
        vec = rng.standard_normal(self.dimension)
        # Normalize to unit length
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    def get_dimension(self) -> int:
        return self.dimension


class OpenAIEmbeddingService(EmbeddingService):
    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self.dimension = 1536
        self.client = None
        self.use_fallback = True

        if api_key:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=api_key)
                self.use_fallback = False
            except Exception:
                logger.warning("OpenAI client failed to load. Falling back to mock embeddings.")

    def get_embedding(self, text: str) -> List[float]:
        if not text:
            return [0.0] * self.dimension

        if not self.use_fallback and self.client:
            try:
                response = self.client.embeddings.create(
                    input=[text],
                    model="text-embedding-ada-002"
                )
                return response.data[0].embedding
            except Exception as e:
                logger.error(f"OpenAI embedding error: {e}. Falling back to mock vector.")

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
