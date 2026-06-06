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

    _TEMP_PATTERN = re.compile(
        r'(?:temp|temperature)(?:\s+is|:)?\s*(\d{2,3}(?:\.\d)?)'
    )
    _BP_PATTERN = re.compile(
        r'(?:bp|blood pressure)(?:\s+is|:)?\s*(\d{2,3})[/\s](\d{2,3})'
    )
    _SINGLE_SYSTOLIC_PATTERN = re.compile(
        r'(?:blood pressure|bp).*?(?:up to|spike to|to|is|:)?\s*(\d{3})(?!\s*(?:/|\d))'
    )

    def extract(self, text: str) -> Dict[str, Any]:
        extracted: Dict[str, Any] = {}

        temp_match = self._TEMP_PATTERN.search(text)
        if temp_match:
            extracted["temperature"] = float(temp_match.group(1))

        bp_match = self._BP_PATTERN.search(text)
        if bp_match:
            extracted["blood_pressure_systolic"] = int(bp_match.group(1))
            extracted["blood_pressure_diastolic"] = int(bp_match.group(2))
        else:
            single_systolic_match = self._SINGLE_SYSTOLIC_PATTERN.search(text)
            if single_systolic_match:
                extracted["blood_pressure_systolic"] = int(single_systolic_match.group(1))

        return extracted
