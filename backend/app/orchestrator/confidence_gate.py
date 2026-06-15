"""
Knowledge Saturation Gate — Evaluates Node 1 -> Node 2 transition.
"""
from typing import Dict, Any, Tuple, List


class KnowledgeSaturationGate:
    """
    Evaluates Completeness × Average Clarity to determine
    Node 1 → Node 2 transition readiness.
    """
    GATE_THRESHOLD = 0.80

    def evaluate(
        self, expected_schema: List[str], extracted_telemetry: Dict[str, Any]
    ) -> Tuple[float, bool]:
        """
        Evaluate if we have gathered enough high-quality data to proceed to Node 2.
        
        Args:
            expected_schema: List of required data variable names (e.g., ['fever_duration', 'chest_pain'])
            extracted_telemetry: The actual data gathered so far. 
                                 Values can be dicts with 'value' and 'clarity' or just simple values.
                                 
        Returns:
            Tuple of (confidence_score, should_transition)
        """
        if not expected_schema:
            return 1.0, True

        v_required = len(expected_schema)
        v_extracted = 0
        total_clarity = 0.0

        for var in expected_schema:
            if var in extracted_telemetry:
                v_extracted += 1
                
                # Assume a simple data structure for extracted telemetry:
                # { "var_name": { "value": "some value", "clarity": 1.0 } }
                # Or fallback to { "var_name": "some value" } with default clarity 1.0
                data_point = extracted_telemetry[var]
                if isinstance(data_point, dict) and "clarity" in data_point:
                    clarity = float(data_point["clarity"])
                else:
                    # If it's a simple value, we assume high clarity (1.0)
                    clarity = 1.0
                    
                total_clarity += clarity

        # Completeness (C) = Extracted Variables / Required Variables
        completeness = v_extracted / v_required

        # Average Clarity (Q)
        # If no variables extracted, average clarity is 0
        avg_clarity = (total_clarity / v_extracted) if v_extracted > 0 else 0.0

        # Confidence = Completeness × Average Clarity
        confidence_score = completeness * avg_clarity
        should_transition = confidence_score >= self.GATE_THRESHOLD

        return confidence_score, should_transition
