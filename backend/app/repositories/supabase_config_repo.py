"""
Supabase Config Repository — ConfigRepository implementation.

Handles persistence for expert_twin_configs table.
Single Responsibility: Only config CRUD operations.
"""
from typing import List, Dict, Any, Optional
from uuid import UUID
import logging

from backend.app.core.interfaces.repositories import ConfigRepository
from backend.app.repositories.base import SupabaseClientMixin

logger = logging.getLogger(__name__)


class SupabaseConfigRepository(SupabaseClientMixin, ConfigRepository):
    """
    Concrete implementation of ConfigRepository backed by Supabase.
    Falls back to in-memory dictionary store when credentials are unavailable.
    """

    def __init__(self, url: str = "", key: str = ""):
        super().__init__(url, key)
        if self.use_mock:
            self._configs: Dict[str, Dict[str, Any]] = {}

    async def save_expert_config(
        self,
        config_id: UUID,
        expert_id: UUID,
        workflow_config: Dict[str, Any],
        active_version: str,
        is_feasible: bool,
        validation_errors: List[str],
    ) -> Dict[str, Any]:
        cid_str = str(config_id)
        eid_str = str(expert_id)
        record = {
            "config_id": cid_str,
            "expert_id": eid_str,
            "workflow_config": workflow_config,
            "active_version": active_version,
            "is_feasible": is_feasible,
            "validation_errors": validation_errors,
        }

        if self.use_mock:
            self._configs[cid_str] = record
            return record

        res = self.client.table("expert_twin_configs").upsert(record).execute()
        return res.data[0] if res.data else record

    async def get_expert_config(self, config_id: UUID) -> Optional[Dict[str, Any]]:
        cid_str = str(config_id)

        if self.use_mock:
            return self._configs.get(cid_str)

        res = (
            self.client.table("expert_twin_configs")
            .select("*")
            .eq("config_id", cid_str)
            .execute()
        )
        return res.data[0] if res.data else None

    async def list_configs(self, expert_id: UUID) -> List[Dict[str, Any]]:
        eid_str = str(expert_id)
        
        if self.use_mock:
            return [c for c in self._configs.values() if c.get("expert_id") == eid_str]
            
        res = (
            self.client.table("expert_twin_configs")
            .select("config_id, active_version, updated_at")
            .eq("expert_id", eid_str)
            .execute()
        )
        return res.data if res.data else []
