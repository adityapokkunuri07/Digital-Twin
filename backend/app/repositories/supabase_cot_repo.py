"""
Supabase CoT Repository — CotRepository implementation.

Handles persistence for cot_nodes and cot_edges tables.
Single Responsibility: Only Chain of Thought graph operations.
"""
from typing import List, Dict, Any
from uuid import UUID, uuid4
import logging

from backend.app.core.interfaces.repositories import CotRepository
from backend.app.repositories.base import SupabaseClientMixin

logger = logging.getLogger(__name__)


class SupabaseCotRepository(SupabaseClientMixin, CotRepository):
    """
    Concrete implementation of CotRepository backed by Supabase.
    Falls back to in-memory list store when credentials are unavailable.
    """

    def __init__(self, url: str = "", key: str = ""):
        super().__init__(url, key)
        if self.use_mock:
            self._cot_nodes: Dict[str, List[Dict[str, Any]]] = {}
            self._cot_edges: Dict[str, List[Dict[str, Any]]] = {}

    async def save_cot_nodes(
        self, config_id: UUID, nodes: List[Dict[str, Any]]
    ) -> None:
        cid_str = str(config_id)
        formatted_nodes = []

        for node in nodes:
            formatted_nodes.append({
                "node_id": str(node.get("node_id", uuid4())),
                "config_id": cid_str,
                "title": node.get("title", ""),
                "node_type": node.get("node_type", "intake"),
                "content": node.get("content", ""),
                "metadata": node.get("metadata", {}),
            })

        if self.use_mock:
            self._cot_nodes[cid_str] = formatted_nodes
            return

        if formatted_nodes:
            self.client.table("cot_nodes").upsert(formatted_nodes).execute()

    async def get_cot_nodes(self, config_id: UUID) -> List[Dict[str, Any]]:
        cid_str = str(config_id)

        if self.use_mock:
            return self._cot_nodes.get(cid_str, [])

        res = (
            self.client.table("cot_nodes")
            .select("*")
            .eq("config_id", cid_str)
            .execute()
        )
        return res.data if res.data else []

    async def save_cot_edges(
        self, config_id: UUID, edges: List[Dict[str, Any]]
    ) -> None:
        cid_str = str(config_id)
        formatted_edges = []

        for edge in edges:
            formatted_edges.append({
                "edge_id": str(edge.get("edge_id", uuid4())),
                "config_id": cid_str,
                "source_node_id": str(edge["source_node_id"]),
                "target_node_id": str(edge["target_node_id"]),
                "relationship_type": edge.get("relationship_type", "related_to"),
            })

        if self.use_mock:
            self._cot_edges[cid_str] = formatted_edges
            return

        if formatted_edges:
            self.client.table("cot_edges").upsert(formatted_edges).execute()

    async def get_cot_edges(self, config_id: UUID) -> List[Dict[str, Any]]:
        cid_str = str(config_id)

        if self.use_mock:
            return self._cot_edges.get(cid_str, [])

        res = (
            self.client.table("cot_edges")
            .select("*")
            .eq("config_id", cid_str)
            .execute()
        )
        return res.data if res.data else []
