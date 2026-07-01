"""
Probing Router — Zero-Trust Orchestrator Component.

Classifies incoming messages into categories to determine which workflow 
to route the user to (e.g., pre_consultation, qa, unlearning).
"""
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


class ProbingRouter:
    """
    Evaluates the intent of a user's initial query before routing them to a specific workflow.
    """

    def __init__(self, llm_service=None):
        self._llm_service = llm_service

    def determine_workflow(self, text: str) -> Tuple[str, str]:
        """
        Classifies the intent of the message to a specific workflow.
        Returns:
            Tuple (workflow_id, message)
            - workflow_id: 'pre_consultation', 'qa', 'unlearning', or 'clarify'
            - message: Follow-up message if clarification is needed
        """
        text_lower = text.lower()
        
        # Simple heuristics for routing
        medical_keywords = ["pain", "hurt", "fever", "cough", "symptom", "sick", "doctor", "appointment", "prescribe", "medication", "pill", "stomach", "headache"]
        qa_keywords = ["who are you", "what is this", "how does this work", "help", "hello", "hi"]
        
        if any(kw in text_lower for kw in medical_keywords):
            return "pre_consultation", ""
            
        if any(kw in text_lower for kw in qa_keywords) and len(text_lower) < 50:
            return "qa", ""
            
        if self._llm_service and not self._llm_service.use_fallback:
            # In a full implementation, we'd prompt the LLM here to classify against available workflows.
            # Using simple heuristics for now.
            pass

        # If ambiguous, stay in probing and ask for clarification
        return "clarify", "Could you provide a bit more detail about what you need help with?"
