"""
Onboarding Service — Business logic for AI Journalist onboarding.

Single Responsibility: Orchestrates interview analysis, CoT extraction,
persistence, and export projection for the onboarding workflow.
"""
from typing import Dict, Any, Tuple
from uuid import UUID
import logging

from backend.app.core.interfaces.repositories import ConfigRepository, CotRepository
from backend.app.core.interfaces.export import ExportService
from backend.app.services.journalist_service import AIOnboardingJournalist

logger = logging.getLogger(__name__)


class OnboardingService:
    """
    Encapsulates all business logic related to expert onboarding:
    - Transcript analysis and saturation scoring
    - Chain of Thought extraction
    - Persistence and export projection
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
        self._journalist = AIOnboardingJournalist()

    async def analyze_interview(
        self, transcript: str
    ) -> Tuple[float, bool, str]:
        """
        Analyze an onboarding transcript for knowledge saturation.

        Returns:
            Tuple of (saturation_score, is_satisfied, next_prompt).
        """
        return await self._journalist.analyze_onboarding_session(transcript)

    async def finalize_onboarding(
        self, config_id: UUID, transcript: str
    ) -> Dict[str, Any]:
        """
        Finalize an onboarding session: validate saturation, extract CoT,
        persist nodes/edges, and project to Obsidian.

        Raises:
            ValueError: If saturation score is below 0.90 threshold.

        Returns:
            Dict with status, node count, and edge count.
        """
        saturation = self._journalist.calculate_saturation(transcript)

        if saturation < 0.90:
            raise ValueError(
                f"Cannot finalize onboarding. Saturation score is {saturation:.2f} "
                f"(required: >= 0.90)."
            )

        # Extract CoT nodes and edges from transcript
        nodes, edges = self._journalist.extract_chain_of_thought(transcript)

        # Persist to database
        await self._cot_repo.save_cot_nodes(config_id, nodes)
        await self._cot_repo.save_cot_edges(config_id, edges)

        # Project to Obsidian audit plane
        config_record = await self._config_repo.get_expert_config(config_id)
        if config_record:
            try:
                self._export_service.export_config(config_record, nodes, edges)
            except Exception as e:
                logger.error(f"Export projection failed during onboarding: {e}")

        return {
            "status": "success",
            "nodes_count": len(nodes),
            "edges_count": len(edges),
        }
