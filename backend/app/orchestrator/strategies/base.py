"""
Processing Strategy ABC — Strategy Design Pattern for Node 2.

Defines the contract for dynamic execution strategies within the Data Processing node.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple, List


class ProcessingStrategy(ABC):
    """
    Abstract strategy for processing patient conversational data into structured formats
    and evaluating against deterministic thresholds.
    """

    @abstractmethod
    async def process(
        self, 
        patient_data: Dict[str, Any], 
        thresholds: List[Dict[str, Any]], 
        context: str,
        **kwargs
    ) -> Tuple[Dict[str, Any], List[str]]:
        """
        Process the patient data against established clinical thresholds.

        Args:
            patient_data: Extracted patient telemetry (e.g. from Node 1 or raw text).
            thresholds: List of threshold rules specific to the current workflow task 
                        (hydrated from the immutable session snapshot).
            context: Additional medical context from RAG.

        Returns:
            Tuple of (processed_data_dict, escalation_reasons_list).
            If escalation_reasons_list is non-empty, the orchestrator should immediately
            route to Node 3 (Human Intercept).
        """
        ...
