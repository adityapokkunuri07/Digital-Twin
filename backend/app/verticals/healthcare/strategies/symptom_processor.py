"""
Symptom Processor Strategy — Dynamic parsing of symptoms against DB rules.
"""
from typing import Dict, Any, Tuple, List
import logging

from backend.app.orchestrator.strategies.base import ProcessingStrategy

logger = logging.getLogger(__name__)


class SymptomProcessor(ProcessingStrategy):
    """
    Parses conversational symptom data and evaluates against explicit entity thresholds.
    """
    
    async def process(
        self, 
        patient_data: Dict[str, Any], 
        thresholds: List[Dict[str, Any]], 
        context: str
    ) -> Tuple[Dict[str, Any], List[str]]:
        
        extracted = {}
        escalations = []
        
        # 1. Look for recognized entity names in patient data
        # In a full implementation, we'd use the LLM to map colloquial terms to these entities
        for rule in thresholds:
            entity = rule.get("entity_name", "")
            if not entity:
                continue
                
            # Check if this entity is in the gathered telemetry
            # (assuming telemetry already mapped colloquial -> strict token)
            if entity in patient_data:
                val = patient_data[entity]
                extracted[entity] = val
                
                # Check min/max numeric bounds if value is numeric
                try:
                    num_val = float(val)
                    min_val = rule.get("min_allowable_value")
                    max_val = rule.get("max_allowable_value")
                    
                    if min_val is not None and num_val < float(min_val):
                        escalations.append(f"{entity} ({num_val}) is below minimum threshold ({min_val})")
                    if max_val is not None and num_val > float(max_val):
                        escalations.append(f"{entity} ({num_val}) exceeds maximum threshold ({max_val})")
                except (ValueError, TypeError):
                    pass # Not a numeric value
                    
                # Check critical escalation triggers (string array)
                triggers = rule.get("critical_escalation_triggers", [])
                str_val = str(val).lower()
                for trigger in triggers:
                    if trigger.lower() in str_val:
                        escalations.append(f"Critical trigger '{trigger}' detected in {entity}")

        return extracted, escalations
