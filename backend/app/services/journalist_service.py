import re
from typing import List, Dict, Any, Tuple
from uuid import uuid4
import logging

logger = logging.getLogger(__name__)

class AIOnboardingJournalist:
    def __init__(self, target_saturation: float = 0.90):
        self.target_saturation = target_saturation

    def calculate_saturation(self, transcript: str) -> float:
        """
        Calculates saturation based on the presence of key clinical concepts:
        - Intake / Symptoms
        - Evaluation / Criteria / Limits
        - Action / Escalation / Dispatch
        Also weights based on text length.
        """
        if not transcript or len(transcript.strip()) < 10:
            return 0.0

        score = 0.0
        text = transcript.lower()

        # Check key semantic sections
        keywords = {
            "intake": ["intake", "symptom", "vital", "patient", "complain", "temp", "blood pressure"],
            "evaluation": ["evaluate", "assess", "diagnose", "criteria", "threshold", "medical history"],
            "action": ["action", "treatment", "prescribe", "escalate", "schedule", "dispatch", "emergency"]
        }

        matches = 0
        for category, list_of_words in keywords.items():
            found = False
            for w in list_of_words:
                if w in text:
                    found = True
            if found:
                matches += 1

        # Base score from keyword matching (each category gives 0.25)
        score += matches * 0.25

        # Length score (up to 0.25 for transcripts over 500 chars)
        len_score = min(0.25, len(transcript) / 2000.0)
        score += len_score

        return min(1.0, score)

    async def analyze_onboarding_session(
        self, session_transcript: str
    ) -> Tuple[float, bool, str]:
        """
        Analyzes a session transcript.
        Returns:
            Tuple[float, bool, str]: (saturation_score, is_satisfied, next_prompt)
        """
        saturation = self.calculate_saturation(session_transcript)
        is_satisfied = saturation >= self.target_saturation

        if is_satisfied:
            next_prompt = "Onboarding completed successfully. Saturation limit achieved."
        else:
            # Guide prompt based on what's missing in keywords
            text = session_transcript.lower()
            if not any(w in text for w in ["intake", "symptom", "vital"]):
                next_prompt = "Can you detail how you perform the initial intake? What symptoms or vitals do you collect first?"
            elif not any(w in text for w in ["evaluate", "criteria", "threshold"]):
                next_prompt = "How do you evaluate those findings? What specific limits or criteria do you look for?"
            else:
                next_prompt = "Once evaluation is done, what actions or escalations should the twin coordinate?"

        return saturation, is_satisfied, next_prompt

    def extract_chain_of_thought(
        self, session_transcript: str
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Extracts structured Chain of Thought (CoT) nodes and relational edges from the transcript.
        """
        nodes = []
        edges = []

        # Generate a set of 3 standard clinical nodes (Intake, Evaluation, Action)
        # populated with segments of the transcript
        node_id_intake = uuid4()
        node_id_eval = uuid4()
        node_id_action = uuid4()

        # Extract text snippets
        sentences = [s.strip() for s in session_transcript.split(".") if s.strip()]
        
        intake_content = "Vitals check and primary symptom gathering."
        eval_content = "Evaluate findings against standard criteria and check boundaries."
        action_content = "Coordinate treatment paths or route to physician escalation."

        if len(sentences) >= 3:
            intake_content = ". ".join(sentences[:len(sentences)//3]) + "."
            eval_content = ". ".join(sentences[len(sentences)//3 : 2*len(sentences)//3]) + "."
            action_content = ". ".join(sentences[2*len(sentences)//3:]) + "."
        elif len(sentences) == 2:
            intake_content = sentences[0] + "."
            eval_content = sentences[1] + "."

        nodes.append({
            "node_id": node_id_intake,
            "title": "Onboarding Intake Gate",
            "node_type": "intake",
            "content": intake_content,
            "metadata": {}
        })

        nodes.append({
            "node_id": node_id_eval,
            "title": "Onboarding Evaluation Gate",
            "node_type": "evaluation",
            "content": eval_content,
            "metadata": {}
        })

        nodes.append({
            "node_id": node_id_action,
            "title": "Onboarding Action Gate",
            "node_type": "action",
            "content": action_content,
            "metadata": {}
        })

        # Add relationships
        edges.append({
            "edge_id": uuid4(),
            "source_node_id": node_id_intake,
            "target_node_id": node_id_eval,
            "relationship_type": "requires"
        })

        edges.append({
            "edge_id": uuid4(),
            "source_node_id": node_id_eval,
            "target_node_id": node_id_action,
            "relationship_type": "requires"
        })

        return nodes, edges
