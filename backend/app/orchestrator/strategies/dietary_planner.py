"""
Dietary Planner Strategy — Synthesizes a dietary plan based on patient telemetry and medical context.
"""
from typing import Dict, Any, Tuple, List
import logging
import json

from backend.app.orchestrator.strategies.base import ProcessingStrategy

logger = logging.getLogger(__name__)

class DietaryPlanner(ProcessingStrategy):
    """
    Uses the LLM to synthesize a dietary plan based on the patient's vitals, symptoms,
    history (telemetry), and the provided RAG knowledge context.
    """
    
    async def process(
        self, 
        patient_data: Dict[str, Any], 
        thresholds: List[Dict[str, Any]], 
        context: str,
        **kwargs
    ) -> Tuple[Dict[str, Any], List[str]]:
        
        extracted = {}
        escalations = []
        
        llm_service = kwargs.get("llm_service")
        
        if not llm_service:
            logger.error("DietaryPlanner requires llm_service, but none was provided.")
            extracted["dietary_plan"] = "Error: Dietary planner unavailable (missing LLM service)."
            return extracted, escalations
            
        system_prompt = (
            "You are an expert Clinical Dietitian. Your task is to synthesize a structured "
            "and actionable dietary plan based on the provided patient vitals, symptoms, history, "
            "and the doctor's knowledge base guidelines.\n\n"
            "Format the output as a clear, concise medical dietary recommendation string. "
            "Do NOT include conversational filler, just the plan."
        )
        
        user_prompt = (
            f"Patient Telemetry:\n{json.dumps(patient_data, indent=2)}\n\n"
            f"Doctor's Knowledge Base Context:\n{context}\n\n"
            "Please generate a comprehensive dietary plan."
        )
        
        try:
            # We can use generate_content from llm_service.client
            # Wait, GeminiLLMService has a client.
            if hasattr(llm_service, "client") and llm_service.client:
                response = llm_service.client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[system_prompt, user_prompt]
                )
                plan = response.text.strip()
            else:
                plan = "Dietary plan generation is currently running in mock mode."
                
            extracted["dietary_plan"] = plan
            
        except Exception as e:
            logger.error(f"Dietary planner LLM generation failed: {e}")
            extracted["dietary_plan"] = f"Failed to generate dietary plan: {str(e)}"
            
        return extracted, escalations
