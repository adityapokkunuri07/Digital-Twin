"""
knowledge_ingestion.py — Expert Knowledge Extractor
===================================================
Uses an LLM to extract structured task steps from raw expert interviews
and inserts them into the knowledge_hub table.
"""
import os
import json
from openai import OpenAI
from backend.app.services.supabase_client import SupabaseService
from dotenv import load_dotenv

load_dotenv(override=True)

class KnowledgeIngestionService:
    def __init__(self):
        api_key = os.environ.get("OPENAI_API_KEY")
        self.client = OpenAI(api_key=api_key) if api_key else None
        self.db = SupabaseService()

    def _build_dynamic_prompt(self) -> str:
        if not self.db.client:
            return "You are a precise data extraction parser. Return an empty array []."
            
        # 1. Fetch available tasks
        tasks_res = self.db.client.table("tasks").select("id, name").execute()
        tasks = tasks_res.data if tasks_res.data else []
        task_list_str = "\n".join([f"- {t['name']}" for t in tasks])

        # 2. Fetch available skills (tools)
        skills_res = self.db.client.table("skill_definitions").select("skill_name").execute()
        skills = skills_res.data if skills_res.data else []
        skill_list_str = "\n".join([f"- {s['skill_name']}" for s in skills])

        prompt = f"""You are a precise data extraction parser. Read the following text.

Your Goal: Extract all rules, principles, or steps related to the requested task.

Available Tasks (Taxonomy): 
{task_list_str}

Extract each rule or principle and format your response EXACTLY as this JSON array schema:
[
  {{
    "task_boundary": "Task Name matching one of the Available Tasks exactly",
    "execution_order": 1,
    "rule": "The specific instruction from the expert",
    "required_action": "tag_representing_skill" 
  }}
]

Allowed `required_action` tags (Must be exactly one of these):
{skill_list_str}

Return ONLY the JSON array. Do not return an empty array unless the text is completely blank.
"""
        return prompt

    def ingest_transcript(self, expert_id: str, transcript: str) -> list:
        if not self.client:
            print("[KNOWLEDGE_INGESTION] OPENAI_API_KEY not set. Cannot parse transcript.")
            return []

        try:
            dynamic_prompt = self._build_dynamic_prompt()
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": dynamic_prompt},
                    {"role": "user", "content": transcript},
                ],
                temperature=0.1,
            )

            raw = response.choices[0].message.content
            # Strip markdown formatting if any
            if raw.startswith("```json"):
                raw = raw.strip("```json").strip("```").strip()
            
            steps = json.loads(raw)
            if not isinstance(steps, list):
                steps = []

            inserted_records = []
            for step in steps:
                record = {
                    "expert_id": expert_id,
                    "task_boundary": step.get("task_boundary"),
                    "execution_order": step.get("execution_order", 0),
                    "rule_text": step.get("rule", ""),
                    "required_action": step.get("required_action", "unknown")
                }
                
                # Insert into Supabase
                res = self.db.client.table("knowledge_hub").insert(record).execute()
                if res.data:
                    inserted_records.extend(res.data)

            print(f"[KNOWLEDGE_INGESTION] Successfully ingested {len(inserted_records)} rules for expert {expert_id}")
            return inserted_records

        except Exception as e:
            print(f"[KNOWLEDGE_INGESTION] Failed to parse transcript: {e}")
            return []
