from backend.app.orchestrator.strategies.base import ProcessingStrategy
from backend.app.orchestrator.strategies.registry import StrategyRegistry
from backend.app.orchestrator.strategies.symptom_processor import SymptomProcessor
from backend.app.orchestrator.strategies.lab_report_processor import LabReportProcessor
from backend.app.orchestrator.strategies.vitals_validator import VitalsValidator

# Register known strategies at import time
StrategyRegistry.register("SYMPTOM_PARSER", SymptomProcessor())
StrategyRegistry.register("LAB_REPORT_ANALYSIS", LabReportProcessor())
StrategyRegistry.register("VITALS_VALIDATION", VitalsValidator())

__all__ = [
    "ProcessingStrategy",
    "StrategyRegistry",
    "SymptomProcessor",
    "LabReportProcessor",
    "VitalsValidator"
]
