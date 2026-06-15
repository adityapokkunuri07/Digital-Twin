"""
Safety Rule ABC — Open/Closed Principle.

Defines the contract for pluggable anomaly detection rules.
New safety rules (lab thresholds, medication interactions, etc.)
can be added without modifying the state machine core.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple


class SafetyRule(ABC):
    """
    Abstract contract for evaluating anomaly/escalation conditions.
    Each rule checks one specific safety concern independently.
    """

    @abstractmethod
    def evaluate(
        self, gathered_data: Dict[str, Any], classification_score: float, thresholds: list = None
    ) -> Tuple[bool, str]:
        """
        Evaluate whether an anomaly condition is triggered.

        Args:
            gathered_data: All variables gathered during the session.
            classification_score: RAG retrieval confidence score.

        Returns:
            Tuple of (is_anomaly, reason_string).
            If is_anomaly is False, reason_string should be empty.
        """
        ...
