"""
Unlearning Service — Mom & Child Unlearning Protocol (Vector Tombstoning).

Single Responsibility: Handles the complete unlearning workflow —
marking nodes as retracted, injecting rationale metadata,
and projecting changes to the export plane.

Extracted from the monolithic endpoints.py unlearn_nodes handler.
"""
from typing import Dict, Any, List
from uuid import UUID
import logging

from backend.app.core.interfaces.repositories import ConfigRepository, CotRepository
from backend.app.core.interfaces.export import ExportService

logger = logging.getLogger(__name__)


class UnlearningService:
    """
    Implements the Mom & Child unlearning protocol:
    1. Mark specified CoT nodes as unlearned (vector tombstoning)
    2. Inject unlearning rationale into node metadata
    3. Prefix content with [RETRACTED]
    4. Persist changes
    5. Project updated state to export plane
    """

    def __init__(
        self,
        config_repo: ConfigRepository,
        cot_repo: CotRepository,
        export_service: ExportService,
    ):
        self._config_repo = config_repo
        self._cot_repo = cot_repo
        self._export_service = export_service

    async def unlearn_nodes(
        self, config_id: UUID, node_ids: List[UUID], rationale: str
    ) -> Dict[str, Any]:
        """
        Execute the unlearning protocol for specified nodes.

        Args:
            config_id: The expert twin configuration ID.
            node_ids: List of CoT node IDs to tombstone.
            rationale: Expert's explicit unlearning rationale.

        Returns:
            Dict with status and list of unlearned node IDs.
        """
        nodes = await self._cot_repo.get_cot_nodes(config_id)
        edges = await self._cot_repo.get_cot_edges(config_id)

        unlearn_ids_str = [str(x) for x in node_ids]
        updated_nodes = []

        for node in nodes:
            nid_str = str(node["node_id"])
            if nid_str in unlearn_ids_str:
                # Vector Tombstoning: mark as unlearned in metadata
                node["metadata"]["unlearned"] = True
                node["metadata"]["unlearning_reason"] = rationale
                node["content"] = "[RETRACTED] " + node["content"]
                logger.info(f"Tombstoned node {nid_str} with rationale: {rationale}")
            updated_nodes.append(node)

        # Persist updated nodes
        await self._cot_repo.save_cot_nodes(config_id, updated_nodes)

        # Project to Obsidian Vault
        config_record = await self._config_repo.get_expert_config(config_id)
        if config_record:
            try:
                self._export_service.export_config(
                    config_record, updated_nodes, edges
                )
            except Exception as e:
                logger.error(f"Export projection failed during unlearning: {e}")

        return {
            "status": "success",
            "unlearned_nodes": unlearn_ids_str,
        }
