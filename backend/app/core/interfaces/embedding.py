"""
Embedding Service Interface — Dependency Inversion Principle (DIP)

Defines the contract for vector embedding generation.
Implementations: LocalTransformerEmbeddingService, GeminiEmbeddingService.
"""
from abc import ABC, abstractmethod
from typing import List


class EmbeddingService(ABC):
    """
    Abstract contract for text-to-vector embedding generation.
    All RAG and ingestion services depend on this interface, never on a concrete implementation.
    """

    @abstractmethod
    def get_embedding(self, text: str) -> List[float]:
        """
        Generate a dense vector embedding for the given text.

        Args:
            text: Input text to encode.

        Returns:
            A list of floats representing the embedding vector.
        """
        ...

    @abstractmethod
    def get_dimension(self) -> int:
        """
        Return the dimensionality of embeddings produced by this service.

        Returns:
            Integer dimension (e.g. 384 for MiniLM, 768 for Gemini).
        """
        ...
