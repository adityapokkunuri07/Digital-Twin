"""
Supabase Pre-Consultation Repository — PreConsultRepository implementation.
"""
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime
import logging

from backend.app.core.interfaces.repositories import PreConsultRepository
from backend.app.repositories.base import SupabaseClientMixin

logger = logging.getLogger(__name__)


class SupabasePreConsultRepository(SupabaseClientMixin, PreConsultRepository):
    """
    Concrete implementation of PreConsultRepository backed by Supabase.
    Falls back to mock mode if credentials are unavailable.
    """

    def __init__(self, url: str = "", key: str = ""):
        super().__init__(url, key)
        if self.use_mock:
            self._sessions: Dict[str, Dict[str, Any]] = {}
            self._logs: List[Dict[str, Any]] = []
            self._summaries: List[Dict[str, Any]] = []
            self._appointments: List[Dict[str, Any]] = []

    async def create_session(
        self, patient_id: UUID, config_id: UUID, workflow_id: UUID, configuration_snapshot: Dict[str, Any]
    ) -> Dict[str, Any]:
        record = {
            "patient_id": str(patient_id),
            "config_id": str(config_id),
            "status": "GATHERING",
            "current_confidence_score": 0.0,
            "turn_count": 0,
            "current_extracted_entities": {},
            "assigned_actor": "TWIN",
            "extracted_telemetry": {},
            "configuration_snapshot": configuration_snapshot
        }
        if workflow_id:
            record["workflow_id"] = str(workflow_id)
        
        if self.use_mock:
            session_id = str(UUID(int=1)) # Mock UUID
            record["session_id"] = session_id
            self._sessions[session_id] = record
            return record
            
        res = self.client.table("pre_consultation_sessions").insert(record).execute()
        return res.data[0] if res.data else record

    async def get_session(self, session_id: UUID) -> Optional[Dict[str, Any]]:
        sid_str = str(session_id)
        if self.use_mock:
            return self._sessions.get(sid_str)
            
        res = self.client.table("pre_consultation_sessions").select("*, patients!fk_patient(full_name, email)").eq("session_id", sid_str).execute()
        return res.data[0] if res.data else None

    async def update_session_state(
        self, 
        session_id: UUID, 
        status: str, 
        confidence_score: float, 
        increment_turn: bool = False,
        current_entities: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        sid_str = str(session_id)
        
        updates: Dict[str, Any] = {
            "status": status,
            "current_confidence_score": confidence_score
        }
        
        if current_entities is not None:
            updates["current_extracted_entities"] = current_entities
            
        if self.use_mock:
            if sid_str in self._sessions:
                self._sessions[sid_str].update(updates)
                if increment_turn:
                    self._sessions[sid_str]["turn_count"] += 1
            return self._sessions.get(sid_str, {})
            
        # In Supabase, if we need to increment we have to fetch or use RPC, 
        # but for simplicity since we usually know the turn_count, we can just 
        # fetch the current turn_count and update.
        # Alternatively, Supabase allows updates with mathematical expressions 
        # but the python client doesn't support it directly without RPC.
        # For this implementation, we will fetch and update.
        if increment_turn:
            current = await self.get_session(session_id)
            if current:
                updates["turn_count"] = current.get("turn_count", 0) + 1
                
        res = self.client.table("pre_consultation_sessions").update(updates).eq("session_id", sid_str).execute()
        return res.data[0] if res.data else {}

    async def append_interaction_log(
        self, 
        session_id: UUID, 
        sender_type: str, 
        message_text: str, 
        extracted_entities: Dict[str, Any], 
        turn_index: int
    ) -> Dict[str, Any]:
        record = {
            "session_id": str(session_id),
            "sender": sender_type,
            "message_text": message_text,
            "extracted_entities": extracted_entities,
            "turn_index": turn_index
        }
        
        if self.use_mock:
            self._logs.append(record)
            return record
            
        res = self.client.table("interaction_logs").insert(record).execute()
        return res.data[0] if res.data else record

    async def get_interaction_logs(self, session_id: UUID) -> List[Dict[str, Any]]:
        sid_str = str(session_id)
        if self.use_mock:
            return sorted([l for l in self._logs if l["session_id"] == sid_str], key=lambda x: x["turn_index"])
            
        res = self.client.table("interaction_logs").select("*").eq("session_id", sid_str).order("turn_index", desc=False).execute()
        return res.data if res.data else []

    async def atomic_insert_summary_and_update_state(
        self, 
        session_id: UUID, 
        structured_data: Dict[str, Any], 
        summary_embedding: List[float]
    ) -> None:
        if self.use_mock:
            # Mock behavior: update session state and append summary
            sid_str = str(session_id)
            if sid_str in self._sessions:
                if self._sessions[sid_str]["status"] in ["SYNTHESIZING", "SYNTHESIZING_PARTIAL"]:
                    self._sessions[sid_str]["status"] = "PENDING_REVIEW"
                    self._summaries.append({
                        "session_id": sid_str,
                        "structured_clinical_data": structured_data,
                        "summary_embedding": summary_embedding,
                        "order_index": len(self._summaries) + 1
                    })
            return
            
        self.client.rpc("atomic_insert_summary_and_update_state", {
            "p_session_id": str(session_id),
            "p_structured_data": structured_data,
            "p_summary_embedding": summary_embedding
        }).execute()



    async def get_active_sessions(self) -> List[Dict[str, Any]]:
        """Fetch all sessions currently in active/in-progress states."""
        active_statuses = [
            "GATHERING", "SYNTHESIZING", "SYNTHESIZING_PARTIAL",
            "awaiting_user_input", "processing_synthesis", "processing_partial_synthesis"
        ]

        if self.use_mock:
            return [s for s in self._sessions.values() if s.get("status") in active_statuses]

        try:
            res = self.client.table("pre_consultation_sessions") \
                .select("session_id, status, current_confidence_score, turn_count, updated_at, patients!fk_patient(full_name, email)") \
                .in_("status", active_statuses) \
                .order("updated_at", desc=True) \
                .execute()
            return res.data if res.data else []
        except Exception as e:
            logger.error(f"Error fetching active sessions: {e}")
            return []
