# Pluggable Data Extractors — Open/Closed principle
from backend.app.orchestrator.extractors.base import DataExtractor
from backend.app.orchestrator.extractors.vitals_extractor import VitalsExtractor
from backend.app.orchestrator.extractors.symptom_extractor import SymptomExtractor

__all__ = ["DataExtractor", "VitalsExtractor", "SymptomExtractor"]
