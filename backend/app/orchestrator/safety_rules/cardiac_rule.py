"""
Cardiac Safety Rule — Detects potential cardiac symptom escalation.
"""
from typing import Dict, Any, Tuple

from backend.app.orchestrator.safety_rules.base import SafetyRule


class CardiacSafetyRule(SafetyRule):
    """Triggers escalation when chest pain is reported."""

    def evaluate(
        self, gathered_data: Dict[str, Any], classification_score: float
    ) -> Tuple[bool, str]:
        if gathered_data.get("chest_pain", False):
            return True, "Potential cardiac symptom (chest pain) reported"
        return False, ""
