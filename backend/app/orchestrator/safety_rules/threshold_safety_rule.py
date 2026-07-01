"""
Threshold Safety Rule — Evaluates dynamic DB thresholds from the session snapshot.
"""
from typing import Dict, Any, Tuple
import logging

from backend.app.orchestrator.safety_rules.base import SafetyRule

logger = logging.getLogger(__name__)


class ThresholdSafetyRule(SafetyRule):
    """
    Validates extracted telemetry against the deterministic thresholds
    hydrated from `entity_thresholds`.
    """

    def evaluate(
        self, gathered_data: Dict[str, Any], classification_score: float, thresholds: list = None
    ) -> Tuple[bool, str]:
        
        if not thresholds:
            return False, ""
            
        escalations = []
        for rule in thresholds:
            entity = rule.get("entity_name", "")
            if not entity or entity not in gathered_data:
                continue
                
            val = gathered_data[entity]
            
            try:
                num_val = float(val)
                min_val = rule.get("min_allowable_value")
                max_val = rule.get("max_allowable_value")
                
                if min_val is not None and num_val < float(min_val):
                    escalations.append(f"{entity} ({num_val}) critically low (min: {min_val})")
                if max_val is not None and num_val > float(max_val):
                    escalations.append(f"{entity} ({num_val}) critically high (max: {max_val})")
            except (ValueError, TypeError):
                pass
                
            triggers = rule.get("critical_escalation_triggers", [])
            str_val = str(val).lower()
            for trigger in triggers:
                if trigger.lower() in str_val:
                    escalations.append(f"Critical trigger '{trigger}' detected in {entity}")

        if escalations:
            return True, "; ".join(escalations)
            
        return False, ""
