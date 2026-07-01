import json
import logging
from typing import Dict, Any, List
from google import genai
from pydantic import BaseModel, Field

from backend.app.core.config import settings

logger = logging.getLogger(__name__)

class ThresholdSchema(BaseModel):
    entity_name: str
    max_allowable_value: float | None = None
    critical_escalation_triggers: list[str]

class TaskSchema(BaseModel):
    original_description: str
    is_supported: bool
    rejection_reason: str | None = None
    strategy_identifier: str | None = None
    required_variables: list[str] = Field(default_factory=list)
    assigned_executor: str

class WorkflowResponseSchema(BaseModel):
    tasks: list[TaskSchema]
    thresholds: list[ThresholdSchema] = Field(default_factory=list)

class WorkflowGeneratorService:
    def __init__(self):
        if settings.GEMINI_API_KEY:
            self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        else:
            self.client = None
            logger.warning("GEMINI_API_KEY is not set. Workflow Generator will fail.")

    def generate_workflow(self, tasks_input: List[Dict[str, str]], capabilities_menu: str = "") -> Dict[str, Any]:
        """
        Maps natural language tasks to technical Node/Strategy execution paths.
        tasks_input: [{'description': '...', 'actor': 'TWIN'}]
        """
        if not self.client:
            raise ValueError("LLM Client not initialized.")

        system_prompt = (
            "You are an expert Clinical Workflow Architect. Your job is to translate plain English "
            "task descriptions from a doctor into structured JSON that maps to our backend capabilities.\n\n"
            "MENU OF CAPABILITIES:\n"
            f"{capabilities_menu}\n"
            "- GENERAL_INTAKE: Generic conversational data gathering.\n\n"
            "RULES:\n"
            "1. You MUST map each task to one of the above capabilities (strategy_identifier).\n"
            "2. If a task asks for something completely unsupported, "
            "set `is_supported: false` and provide a `rejection_reason`.\n"
            "3. If a task is supported, set `is_supported: true`, choose the closest `strategy_identifier` (or null if it's GENERAL_INTAKE), "
            "and deduce a list of `required_variables`.\n"
            "4. `assigned_executor` MUST be either 'TWIN' (AI) or 'EXPERT' (Human).\n"
            "5. Based on the tasks, deduce and generate reasonable `thresholds` for critical variables to ensure safety."
        )

        user_prompt = f"Map these tasks:\n{json.dumps(tasks_input, indent=2)}"

        try:
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[system_prompt, user_prompt],
                config={
                    "response_mime_type": "application/json",
                    "response_schema": WorkflowResponseSchema,
                    "temperature": 0.1
                }
            )
            return json.loads(response.text)
        except Exception as e:
            logger.error(f"Failed to generate workflow: {e}")
            raise
