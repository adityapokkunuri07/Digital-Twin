"""
Database Service — Backward-Compatible Composition Layer.

This file is DEPRECATED for new code. All new code should import from:
    - backend.app.core.interfaces.repositories (for ABCs)
    - backend.app.repositories.* (for concrete implementations)

This module exists solely to maintain backward compatibility with the test suite
and any external code that still imports `DatabaseService` or `SupabaseDatabaseService`.

It composes all 4 segregated repositories into a single unified class that
implements all the old methods. It will be removed in a future version.
"""
from typing import List, Dict, Any, Optional
from uuid import UUID
import logging
import warnings

from backend.app.core.interfaces.repositories import (
    ConfigRepository,
    KnowledgeRepository,
    CotRepository,
    SessionRepository,
)
from backend.app.repositories.supabase_config_repo import SupabaseConfigRepository
from backend.app.repositories.supabase_knowledge_repo import SupabaseKnowledgeRepository
from backend.app.repositories.supabase_cot_repo import SupabaseCotRepository
from backend.app.repositories.supabase_session_repo import SupabaseSessionRepository

logger = logging.getLogger(__name__)


# Re-export the ABC for backward compat imports
DatabaseService = type(
    "DatabaseService",
    (ConfigRepository, KnowledgeRepository, CotRepository, SessionRepository),
    {},
)


class SupabaseDatabaseService(
    ConfigRepository,
    KnowledgeRepository,
    CotRepository,
    SessionRepository,
):
    """
    DEPRECATED: Backward-compatible composition of all 4 segregated repositories.

    New code should inject the specific repository interface it needs:
        ConfigRepository, KnowledgeRepository, CotRepository, or SessionRepository.
    """

    def __init__(self, url: str = "", key: str = ""):
        warnings.warn(
            "SupabaseDatabaseService is deprecated. "
            "Use the segregated repositories from backend.app.repositories instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self._config_repo = SupabaseConfigRepository(url, key)
        self._knowledge_repo = SupabaseKnowledgeRepository(url, key)
        self._cot_repo = SupabaseCotRepository(url, key)
        self._session_repo = SupabaseSessionRepository(url, key)

    # --- ConfigRepository delegation ---

    async def save_expert_config(
        self, config_id: UUID, expert_id: UUID, workflow_config: Dict[str, Any],
        active_version: str, is_feasible: bool, validation_errors: List[str],
    ) -> Dict[str, Any]:
        return await self._config_repo.save_expert_config(
            config_id, expert_id, workflow_config,
            active_version, is_feasible, validation_errors,
        )

    async def get_expert_config(self, config_id: UUID) -> Optional[Dict[str, Any]]:
        return await self._config_repo.get_expert_config(config_id)

    # --- KnowledgeRepository delegation ---

    async def delete_knowledge_chunks(self, config_id: UUID) -> None:
        return await self._knowledge_repo.delete_knowledge_chunks(config_id)

    async def save_knowledge_chunks(
        self, config_id: UUID, chunks: List[Dict[str, Any]]
    ) -> None:
        return await self._knowledge_repo.save_knowledge_chunks(config_id, chunks)

    async def match_knowledge_chunks(
        self, config_id: UUID, embedding: List[float], threshold: float, limit: int, operational_mode: str = None
    ) -> List[Dict[str, Any]]:
        return await self._knowledge_repo.match_knowledge_chunks(
            config_id, embedding, threshold, limit, operational_mode
        )

    async def match_knowledge_chunks_lexical(
        self, config_id: UUID, query_text: str, threshold: float, limit: int, operational_mode: str = None
    ) -> List[Dict[str, Any]]:
        return await self._knowledge_repo.match_knowledge_chunks_lexical(
            config_id, query_text, threshold, limit, operational_mode
        )

    async def get_knowledge_chunk_by_path(
        self, config_id: UUID, parent_path: str
    ) -> Optional[Dict[str, Any]]:
        return await self._knowledge_repo.get_knowledge_chunk_by_path(
            config_id, parent_path,
        )

    # --- CotRepository delegation ---

    async def save_cot_nodes(
        self, config_id: UUID, nodes: List[Dict[str, Any]]
    ) -> None:
        return await self._cot_repo.save_cot_nodes(config_id, nodes)

    async def get_cot_nodes(self, config_id: UUID) -> List[Dict[str, Any]]:
        return await self._cot_repo.get_cot_nodes(config_id)

    async def save_cot_edges(
        self, config_id: UUID, edges: List[Dict[str, Any]]
    ) -> None:
        return await self._cot_repo.save_cot_edges(config_id, edges)

    async def get_cot_edges(self, config_id: UUID) -> List[Dict[str, Any]]:
        return await self._cot_repo.get_cot_edges(config_id)

    # --- SessionRepository delegation ---

    async def get_active_session(
        self, session_id: UUID
    ) -> Optional[Dict[str, Any]]:
        return await self._session_repo.get_active_session(session_id)

    async def save_active_session(
        self, session_id: UUID, conversation_id: UUID, config_id: UUID,
        current_node: str, graph_state: Dict[str, Any],
        is_paused: bool, requires_review: bool,
    ) -> Dict[str, Any]:
        return await self._session_repo.save_active_session(
            session_id, conversation_id, config_id,
            current_node, graph_state, is_paused, requires_review,
        )

    async def create_execution_trace(
        self, session_id: UUID, step_name: str, prompt_used: str,
        response_generated: str, retrieved_chunk_ids: List[UUID],
        classification_score: float,
    ) -> Dict[str, Any]:
        return await self._session_repo.create_execution_trace(
            session_id, step_name, prompt_used,
            response_generated, retrieved_chunk_ids, classification_score,
        )
