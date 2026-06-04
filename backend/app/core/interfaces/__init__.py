# Abstract Contracts — Interface definitions for Dependency Inversion
from backend.app.core.interfaces.repositories import (
    ConfigRepository,
    KnowledgeRepository,
    CotRepository,
    SessionRepository,
)
from backend.app.core.interfaces.embedding import EmbeddingService
from backend.app.core.interfaces.export import ExportService

__all__ = [
    "ConfigRepository",
    "KnowledgeRepository",
    "CotRepository",
    "SessionRepository",
    "EmbeddingService",
    "ExportService",
]
