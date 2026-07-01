"""
Vitals Validator Strategy — Evaluates standard vitals (HR, BP, Temp).
"""
from typing import Dict, Any, Tuple, List
import logging

from backend.app.orchestrator.strategies.base import ProcessingStrategy

logger = logging.getLogger(__name__)


class VitalsValidator(ProcessingStrategy):
    """
    Validates vital signs against thresholds.
    """
    
    async def process(
        self, 
        patient_data: Dict[str, Any], 
        thresholds: List[Dict[str, Any]], 
        context: str
    ) -> Tuple[Dict[str, Any], List[str]]:
        
        extracted = {}
        escalations = []
        
        for rule in thresholds:
            entity = rule.get("entity_name", "")
            if not entity or entity not in patient_data:
                continue
                
            val = patient_data[entity]
            extracted[entity] = val
            
            try:
                num_val = float(val)
                min_val = rule.get("min_allowable_value")
                max_val = rule.get("max_allowable_value")
                
                if min_val is not None and num_val < float(min_val):
                    escalations.append(f"Vitals anomaly: {entity} ({num_val}) below min ({min_val})")
                if max_val is not None and num_val > float(max_val):
                    escalations.append(f"Vitals anomaly: {entity} ({num_val}) above max ({max_val})")
            except (ValueError, TypeError):
                pass

        return extracted, escalations
