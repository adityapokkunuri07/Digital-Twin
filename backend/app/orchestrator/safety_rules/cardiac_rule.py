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
            
        message = gathered_data.get("message", "").lower()
        if "chest pain" in message or "chest tightness" in message or "heart attack" in message:
            return True, "Potential cardiac symptom reported"
            
        return False, ""
