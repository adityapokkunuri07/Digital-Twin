"""
Config Service — Business logic for configuration management.

Single Responsibility: Orchestrates validation, persistence, and export projection
for expert twin configurations. Route handlers delegate to this service.

Depends on abstractions (ConfigRepository, CotRepository, ExportService)
rather than concrete implementations (Dependency Inversion).
"""
from typing import Dict, Any, List, Tuple
from uuid import UUID, uuid4
import logging

from backend.app.core.interfaces.repositories import ConfigRepository, CotRepository
from backend.app.core.interfaces.export import ExportService
from backend.app.services.feasibility_validator import FeasibilityValidator

logger = logging.getLogger(__name__)


class ConfigService:
    """
    Encapsulates all business logic related to expert twin configuration:
    - Feasibility validation
    - Config persistence
    - Obsidian vault projection
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

    def validate_config(
        self, workflow_config: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """Run feasibility validation on a workflow configuration."""
        return FeasibilityValidator.validate_config(workflow_config)

    async def save_config(
        self,
        config_id: UUID | None,
        doctor_id: UUID,
        workflow_config: Dict[str, Any],
        active_version: str,
    ) -> Dict[str, Any]:
        """
        Validate, persist, and project a twin configuration.

        Returns:
            Dict containing: config_id, is_feasible, errors, and the saved record.
        """
        resolved_config_id = config_id or uuid4()

        # 1. Feasibility check
        is_feasible, errors = FeasibilityValidator.validate_config(workflow_config)

        # 2. Persist config
        record = await self._config_repo.save_expert_config(
            resolved_config_id, doctor_id, workflow_config,
            active_version, is_feasible, errors,
        )

        # 3. Project state to Obsidian audit plane
        nodes = await self._cot_repo.get_cot_nodes(resolved_config_id)
        edges = await self._cot_repo.get_cot_edges(resolved_config_id)
        try:
            self._export_service.export_config(record, nodes, edges)
        except Exception as e:
            logger.error(f"Export projection failed: {e}")

        return {
            "status": "success",
            "config_id": resolved_config_id,
            "is_feasible": is_feasible,
            "errors": errors,
            "record": record,
        }
