"""
Configuration-related request/response schemas.

Separated from route handlers per Single Responsibility Principle —
data contracts live independently of HTTP handling logic.
"""
from typing import Dict, Any, List, Optional
from uuid import UUID
from pydantic import BaseModel


class ValidateConfigRequest(BaseModel):
    """Request payload for workflow configuration validation."""
    workflow_config: Dict[str, Any]


class SaveConfigRequest(BaseModel):
    """Request payload for saving/upserting a twin configuration."""
    config_id: Optional[UUID] = None
    expert_id: UUID
    workflow_config: Dict[str, Any]
    active_version: str = "1.0.0"


class IngestDocumentRequest(BaseModel):
    """Request payload for raw text document ingestion into the RAG pipeline."""
    config_id: UUID
    raw_text: str


class UnlearnRequest(BaseModel):
    """Request payload for the Mom & Child unlearning protocol (vector tombstoning)."""
    node_ids: List[UUID]
    rationale: str
