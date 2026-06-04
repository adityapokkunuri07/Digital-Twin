"""
Fever Safety Rule — Detects extreme fever anomaly (>= 103.0°F).
"""
from typing import Dict, Any, Tuple

from backend.app.orchestrator.safety_rules.base import SafetyRule


class FeverSafetyRule(SafetyRule):
    """Triggers escalation when temperature >= 103.0°F is detected."""

    THRESHOLD = 103.0

    def evaluate(
        self, gathered_data: Dict[str, Any], classification_score: float
    ) -> Tuple[bool, str]:
        temperature = gathered_data.get("temperature")
        if temperature is not None and temperature >= self.THRESHOLD:
            return True, f"Extreme fever detected (>={self.THRESHOLD}°F)"
        return False, ""
