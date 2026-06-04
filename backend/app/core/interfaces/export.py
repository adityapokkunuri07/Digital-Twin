"""
Export Service Interface — Dependency Inversion Principle (DIP)

Defines the contract for projecting database state to external audit planes.
Implementations: ObsidianExportService (and potentially future exporters like Notion, Confluence, etc.).
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any


class ExportService(ABC):
    """
    Abstract contract for exporting twin configuration and CoT graph state
    to an external projection plane (e.g. Obsidian Vault, Notion, filesystem).
    """

    @abstractmethod
    def export_config(
        self,
        config: Dict[str, Any],
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]],
    ) -> str:
        """
        Export a complete twin configuration with its associated CoT graph.

        Args:
            config: The expert_twin_configs record.
            nodes: List of CoT node records.
            edges: List of CoT edge records.

        Returns:
            Path or identifier of the primary exported artifact.
        """
        ...
