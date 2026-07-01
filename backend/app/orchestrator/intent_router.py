"""
Intent Router — Zero-Trust Orchestrator Component.

Classifies incoming messages into categories to prevent the state machine
from attempting to extract clinical variables from non-clinical queries
(e.g., "Who are you?", "How does this work?").
"""
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


class IntentRouter:
    """
    Evaluates the intent of a user's query before it reaches Node 1 (Data Gathering).
    """

    def __init__(self, llm_service=None):
        self._llm_service = llm_service

    def resolve_intent(self, text: str) -> Tuple[str, str]:
        """
        Classifies the intent of the message.
        Returns:
            Tuple (intent_type, message)
            - intent_type: 'medical_intake' or 'general_inquiry'
            - message: Pre-canned response or empty string
        """
        text_lower = text.lower()
        
        # Simple heuristic fallback
        general_keywords = ["who are you", "what is this", "how does this work", "help", "hello", "hi"]
        if any(kw in text_lower for kw in general_keywords) and len(text_lower) < 50:
            return "general_inquiry", ""

        if self._llm_service and not self._llm_service.use_fallback:
            # In a full implementation, we'd prompt the LLM here to classify.
            # Using simple heuristics for now.
            pass

        return "medical_intake", ""
