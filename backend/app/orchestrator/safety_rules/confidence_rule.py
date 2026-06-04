"""
Confidence Safety Rule — Detects low-confidence RAG retrieval.
"""
from typing import Dict, Any, Tuple

from backend.app.orchestrator.safety_rules.base import SafetyRule


class ConfidenceSafetyRule(SafetyRule):
    """Triggers escalation when RAG retrieval confidence drops below the zero-trust gate."""

    def __init__(self, confidence_gate: float = 0.85):
        self.confidence_gate = confidence_gate

    def evaluate(
        self, gathered_data: Dict[str, Any], classification_score: float
    ) -> Tuple[bool, str]:
        if classification_score < self.confidence_gate:
            return True, (
                f"Retrieval confidence ({classification_score:.2f}) "
                f"dropped below zero-trust gate ({self.confidence_gate})"
            )
        return False, ""
