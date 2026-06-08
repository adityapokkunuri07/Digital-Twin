"""
Vitals Extractor — Extracts temperature and blood pressure from user input.

Extracted from the monolithic state_machine.py run_step() method
to follow Open/Closed principle.
"""
import re
from typing import Dict, Any

from backend.app.orchestrator.extractors.base import DataExtractor


class VitalsExtractor(DataExtractor):
    """
    Extracts vital sign measurements from natural language input:
    - Temperature (e.g. "temperature is 101", "temp: 99.5")
    - Blood Pressure (e.g. "bp is 120/80", "blood pressure: 130 85")
    """

    # Matches "temperature is 101", "temp: 99.5", etc.
    _TEMP_PATTERN = re.compile(
        r'(?:temp|temperature)(?:\s+is|:)?\s*(\d{2,3}(?:\.\d{1,2})?)'
    )
    # Fallback: bare decimal like "98.4" or "101.2" (typical body temp range)
    _BARE_TEMP_PATTERN = re.compile(
        r'\b(9[0-9]|10[0-9])(?:\.\d{1,2})?\b'
    )
    # Matches "bp is 120/80", "blood pressure: 130 85", or bare "120/80"
    _BP_PATTERN = re.compile(
        r'(?:(?:bp|blood pressure)(?:\s+is|:)?\s*)?(\d{2,3})/(\d{2,3})'
    )
    _SINGLE_SYSTOLIC_PATTERN = re.compile(
        r'(?:blood pressure|bp).*?(?:up to|spike to|to|is|:)?\s*(\d{3})(?!\s*(?:/|\d))'
    )

    def extract(self, text: str) -> Dict[str, Any]:
        extracted: Dict[str, Any] = {}

        # Try explicit "temp 98.6" first, then fall back to bare number
        temp_match = self._TEMP_PATTERN.search(text)
        if temp_match:
            extracted["temperature"] = float(temp_match.group(1))
        else:
            bare_match = self._BARE_TEMP_PATTERN.search(text)
            if bare_match:
                val = float(bare_match.group(0))
                # Only treat as temperature if it looks like a body temp (90-109)
                if 90.0 <= val <= 109.0:
                    extracted["temperature"] = val

        bp_match = self._BP_PATTERN.search(text)
        if bp_match:
            extracted["blood_pressure_systolic"] = int(bp_match.group(1))
            extracted["blood_pressure_diastolic"] = int(bp_match.group(2))
        else:
            single_systolic_match = self._SINGLE_SYSTOLIC_PATTERN.search(text)
            if single_systolic_match:
                extracted["blood_pressure_systolic"] = int(single_systolic_match.group(1))

        return extracted
