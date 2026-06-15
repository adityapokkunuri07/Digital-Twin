import json
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class ContextSynthesizer:
    SYNTHESIS_INTERVAL = 4  # Trigger every N turns

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    def should_synthesize(self, history: List[Dict]) -> bool:
        """Check if enough turns have accumulated since last synthesis."""
        return len(history) > 0 and len(history) % self.SYNTHESIS_INTERVAL == 0

    def synthesize(self, history: List[Dict], gathered_data: Dict) -> Dict[str, Any]:
        """
        Prompt Gemini to extract hard facts from chat history.
        """
        if not self.llm_client:
            logger.warning("No LLM client provided for context synthesis. Returning empty profile.")
            return {}

        chat_history_str = "\n".join([f"{msg.get('role', 'unknown')}: {msg.get('content', '')}" for msg in history])
        
        prompt = (
            "You are a clinical data extraction assistant.\n"
            "From the conversation history below, extract ONLY the following structured facts:\n"
            "- Vitals: temperature, blood_pressure, heart_rate, SpO2\n"
            "- Symptoms: list of (symptom, duration, severity)\n"
            "- Risk Factors: smoking, diabetes, family history, BMI\n"
            "- Timeline: key events with approximate timestamps\n"
            "Return ONLY valid JSON. Do not include conversational filler.\n\n"
            f"History:\n{chat_history_str}"
        )

        try:
            # We assume self.llm_client is the google.genai client
            # The client is usually passed from ZeroTrustOrchestrator or PreConsultService
            response = self.llm_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "temperature": 0.1,
                }
            )
            return json.loads(response.text)
        except Exception as e:
            logger.error(f"Failed to synthesize context: {e}")
            return {}

    def build_optimized_context(
        self, synthesized_profile: Dict, recent_turns: List[Dict], n_recent: int = 3
    ) -> str:
        """
        Build the optimized prompt payload:
        [Synthesized_Profile] + [Last_N_Raw_Turns]
        """
        profile_str = json.dumps(synthesized_profile, indent=2) if synthesized_profile else "None"
        
        # Take the last N user/assistant turns
        recent = recent_turns[-n_recent:] if len(recent_turns) >= n_recent else recent_turns
        recent_str = "\n".join([f"{msg.get('role', msg.get('sender', 'unknown'))}: {msg.get('content', msg.get('message_text', ''))}" for msg in recent])
        
        optimized = (
            "--- SYNTHESIZED PATIENT PROFILE ---\n"
            f"{profile_str}\n\n"
            "--- RECENT CONVERSATION HISTORY ---\n"
            f"{recent_str}"
        )
        return optimized
