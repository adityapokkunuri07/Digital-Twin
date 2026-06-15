"""
Gemini LLM Service — Language Model reasoning and extraction.

Uses Google's Gemini models to perform dynamic reasoning, extraction,
and response generation.
"""
import json
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class GeminiLLMService:
    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self.use_fallback = True
        
        if api_key:
            try:
                from google import genai
                from google.genai import types
                self.client = genai.Client(api_key=api_key)
                self.types = types
                self.use_fallback = False
            except ImportError:
                logger.warning("google-genai package not installed. Falling back to mock LLM.")
            except Exception as e:
                logger.warning(f"Gemini client failed to load: {e}. Falling back to mock LLM.")

    def extract_variables(self, text: str, variables: List[str]) -> Dict[str, Any]:
        """Dynamically extract requested variables from user input."""
        if not variables:
            return {}
        if self.use_fallback:
            logger.warning("Mock LLM extracting variables...")
            return {v: "Mock Extracted Data" for v in variables}
            
        prompt = f"""
You are an expert medical data extraction assistant.
Extract the following variables from the user's input: {variables}.
If a variable is not mentioned or implied in the input, do not include it in the output.
User input: "{text}"
Return ONLY a valid JSON object where keys are the extracted variables.
"""
        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=self.types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.0
                )
            )
            return json.loads(response.text)
        except Exception as e:
            logger.error(f"Error extracting variables: {e}")
            return {}

    def generate_followup(self, missing_inputs: List[str], gathered: Dict[str, Any], context_window: str = "") -> str:
        """Dynamically generate an empathetic follow-up question."""
        if self.use_fallback:
            return f"Could you please tell me about: {', '.join(missing_inputs)}?"
            
        prompt = f"""
You are an empathetic, professional AI doctor assistant.
The patient has already provided the following information: {gathered}.
Additional Context/History:
{context_window}

You need to ask them about these missing variables: {missing_inputs}.
Formulate a natural, conversational, and empathetic follow-up question.
Acknowledge what they've already shared briefly.
If there are many missing inputs, just ask about 1 or 2 at a time so you don't overwhelm them.
Keep it concise and professional.
"""
        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=self.types.GenerateContentConfig(temperature=0.3)
            )
            return response.text.strip()
        except Exception as e:
            logger.error(f"Error generating follow-up: {e}")
            return f"Could you please provide information about: {', '.join(missing_inputs)}?"

    def evaluate_step(self, step_name: str, inputs: Dict[str, Any], outputs: List[str], context_window: str = "") -> Dict[str, Any]:
        """Evaluate an intermediate workflow step using LLM reasoning."""
        if not outputs:
            return {}
        if self.use_fallback:
            return {o: "Mock Evaluated Data" for o in outputs}
            
        prompt = f"""
You are an expert clinical reasoning engine.
Your task is to execute a step in a medical workflow.
Step Name: {step_name}
Inputs available: {inputs}
Additional Medical Context/History (if any): {context_window}

Based on the inputs and clinical knowledge, compute and return the following outputs: {outputs}.
Return ONLY a valid JSON object mapping each requested output variable to its computed value.
"""
        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=self.types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.0
                )
            )
            return json.loads(response.text)
        except Exception as e:
            logger.error(f"Error evaluating step {step_name}: {e}")
            return {}
    