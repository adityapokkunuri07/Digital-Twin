"""
Supabase Session Repository — SessionRepository implementation.

Handles persistence for active_sessions and execution_traces tables.
Single Responsibility: Only session state + telemetry operations.
"""
from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4
import logging

from backend.app.core.interfaces.repositories import SessionRepository
from backend.app.repositories.base import SupabaseClientMixin

logger = logging.getLogger(__name__)


class SupabaseSessionRepository(SupabaseClientMixin, SessionRepository):
    """
    Concrete implementation of SessionRepository backed by Supabase.
    Falls back to in-memory store when credentials are unavailable.
    """

    def __init__(self, url: str = "", key: str = ""):
        super().__init__(url, key)
        if self.use_mock:
            self._sessions: Dict[str, Dict[str, Any]] = {}
            self._traces: List[Dict[str, Any]] = []

    async def get_active_session(
        self, session_id: UUID
    ) -> Optional[Dict[str, Any]]:
        sid_str = str(session_id)

        if self.use_mock:
            return self._sessions.get(sid_str)

        res = (
            self.client.table("active_sessions")
            .select("*")
            .eq("session_id", sid_str)
            .execute()
        )
        return res.data[0] if res.data else None

    async def save_active_session(
        self,
        session_id: UUID,
        conversation_id: UUID,
        config_id: UUID,
        current_node: str,
        graph_state: Dict[str, Any],
        is_paused: bool,
        requires_review: bool,
    ) -> Dict[str, Any]:
        sid_str = str(session_id)
        record = {
            "session_id": sid_str,
            "conversation_id": str(conversation_id),
            "config_id": str(config_id),
            "current_node": current_node,
            "graph_state": graph_state,
            "is_paused": is_paused,
            "requires_review": requires_review,
        }

        if self.use_mock:
            self._sessions[sid_str] = record
            return record

        res = self.client.table("active_sessions").upsert(record).execute()
        return res.data[0] if res.data else record

    async def create_execution_trace(
        self,
        session_id: UUID,
        step_name: str,
        prompt_used: str,
        response_generated: str,
        retrieved_chunk_ids: List[UUID],
        classification_score: float,
    ) -> Dict[str, Any]:
        record = {
            "trace_id": str(uuid4()),
            "session_id": str(session_id),
            "step_name": step_name,
            "prompt_used": prompt_used,
            "response_generated": response_generated,
            "retrieved_chunk_ids": [str(x) for x in retrieved_chunk_ids],
            "classification_score": classification_score,
        }

        if self.use_mock:
            self._traces.append(record)
            return record

        res = self.client.table("execution_traces").insert(record).execute()
        return res.data[0] if res.data else record
