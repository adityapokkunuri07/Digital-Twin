"""
Symptom Extractor — Extracts symptom indicators from user input.

Detects keyword-based symptom patterns like chest pain, shortness of breath, etc.
"""
import re
from typing import Dict, Any

from backend.app.orchestrator.extractors.base import DataExtractor


class SymptomExtractor(DataExtractor):
    """
    Extracts symptom indicators from natural language input:
    - Chest pain / chest tightness
    - Additional symptom patterns can be added here without
      modifying the state machine (Open/Closed).
    """

    _CHEST_PAIN_PATTERN = re.compile(
        r'(?:chest pain|chest tightness|pain in chest)'
    )

    def extract(self, text: str) -> Dict[str, Any]:
        extracted: Dict[str, Any] = {}

        if self._CHEST_PAIN_PATTERN.search(text):
            extracted["chest_pain"] = True

        return extracted
