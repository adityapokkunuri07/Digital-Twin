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

    def generate_assessment(self, gathered: Dict[str, Any], context_window: str = "", history: list = None) -> Dict[str, Any]:
        """Dynamically generate a comprehensive clinical assessment and trigger skills if needed."""
        if self.use_fallback:
            return {"assessment_text": "Based on your information, I will consult the doctor.", "triggered_skill": None}
            
        hist_str = ""
        if history:
            for h in history[-5:]: # last 5 turns
                role = str(h.get("role", "Unknown")).upper()
                hist_str += f"{role}: {h.get('content', '')}\n"
                
        prompt = f"""
You are an expert clinical AI assistant acting as an experienced gynecologist thinking through a case.
The patient has provided the following information: {gathered}.

Recent Conversation History:
{hist_str}

Additional Context and Clinical Guidelines (from expert documents):
{context_window}

Before reaching any conclusion, always:
1. Understand the patient's story and chief concern.
2. Analyze the symptom timeline and explain why the timeline matters.
3. Review menstrual history and reproductive history.
4. Assess lifestyle factors such as stress, sleep, exercise, weight changes, and diet.
5. Evaluate medical history, family history, and risk factors.
6. Assess vital signs and identify clinically significant findings.
7. Identify any red flags that require urgent attention.
8. Recognize symptom patterns instead of evaluating symptoms individually.
9. Generate:
   - Most Likely Diagnosis
   - Alternative Diagnosis
   - Serious Condition That Must Not Be Missed
10. Explicitly explain the evidence supporting each diagnosis.
11. Explicitly explain the evidence against each diagnosis.
12. Apply Dr. Ananya's clinical rules:
    - Treat the patient, not the report.
    - Never diagnose PCOS solely from ultrasound findings.
    - Always consider thyroid disease when evaluating menstrual abnormalities.
    - Symptoms and investigations must support each other.
    - Serious conditions must be excluded before common conditions are assumed.
    - Repeated trends are more valuable than isolated findings.
13. Correlate symptoms, history, risk factors, investigations, and imaging findings.
14. Assign a diagnostic confidence level (High, Moderate, Low).
15. Explain your reasoning process transparently.

Your responses should sound like an experienced gynecologist thinking through a case, not a chatbot giving generic advice.
Whenever possible, explicitly reference the provided clinical guidelines and the patient's specific data.

Keep it structured, clear, and empathetic. Output it as clean conversational paragraphs. Do not use bullet points or bold headers.

Additionally, if the guidelines indicate that a specific automated action or skill should be performed (e.g., SKL_EXPERT_SYNTHESIS, SKL_BASELINE_VIGILANCE, SKL_PRE_OP_GATEKEEPER), specify the skill name and extract the required payload parameters.
If no skill is explicitly needed, set triggered_skill to null.

Output ONLY a JSON object in this format:
{{
  "assessment_text": "The conversational text to show the patient...",
  "triggered_skill": "skill_name_or_null",
  "skill_payload": {{"param1": "value1"}}
}}
"""
        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=self.types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2
                )
            )
            return json.loads(response.text)
        except Exception as e:
            logger.error(f"Error generating assessment: {e}")
            return {"assessment_text": "Based on your information, I will compile this for the doctor's review.", "triggered_skill": None}

    def derive_required_inputs(self, context_window: str, gathered: Dict[str, Any]) -> List[str]:
        """Dynamically determine missing required information based on clinical guidelines."""
        if self.use_fallback or not context_window:
            return []
            
        prompt = f"""
You are an expert clinical AI. Review the following Clinical Guidelines:
{context_window}

The patient has already provided the following information: {gathered}.
Based strictly on the Guidelines, are there any critical data points (symptoms, history, vitals) that the guidelines require but have NOT been gathered yet?
Return ONLY a JSON list of short variable names representing the missing data points.
If all necessary information has been gathered according to the guidelines, return an empty list: []
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
            logger.error(f"Error deriving required inputs: {e}")
            return []
