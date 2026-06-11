"""
task_assembler.py — Dynamic Skill Binding and Blueprint Generation
==================================================================
Queries the knowledge_hub for a given task/expert, maps the required
actions to actual executable skills, and stores the resulting blueprint.
"""
import json
from backend.app.services.supabase_client import SupabaseService

class TaskAssembler:
    def __init__(self):
        self.db = SupabaseService()

    def assemble_blueprint(self, task_name: str, expert_id: str) -> dict:
        """
        Retrieves rules from knowledge_hub, binds skills, and creates a template.
        """
        if not self.db.client:
            return {}

        # 1. Retrieve rules
        res = self.db.client.table("knowledge_hub").select(
            "rule_text, required_action"
        ).eq("task_boundary", task_name).eq("expert_id", expert_id).order("execution_order").execute()
        
        rules_data = res.data or []
        if not rules_data:
            print(f"[TASK_ASSEMBLER] No rules found for task {task_name} and expert {expert_id}")
            return {}

        # 2. Dynamic Skill Binding
        rules = []
        tools = []
        for row in rules_data:
            rules.append(row["rule_text"])
            
            # Use the required_action directly since it now maps to real skill_names
            action = row.get("required_action")
            if action not in tools:
                tools.append(action)

        # 3. Payload Assembly
        template = {
            "task_name": task_name,
            "expert_id": expert_id,
            "rules": rules,
            "tools": tools,
            "target_document_id": "{{TARGET_DOCUMENT_ID}}"
        }

        # 4. Cache to task_blueprints
        existing = self.db.client.table("task_blueprints").select("task_id").eq("task_id", task_name).execute()
        if existing.data:
            self.db.client.table("task_blueprints").update({
                "payload_template": template
            }).eq("task_id", task_name).execute()
        else:
            self.db.client.table("task_blueprints").insert({
                "task_id": task_name,
                "payload_template": template
            }).execute()

        print(f"[TASK_ASSEMBLER] Assembled and cached blueprint for {task_name}")
        return template

    def execute_task(self, task_name: str, runtime_context: dict) -> dict:
        """
        Fetches the pre-built template from task_blueprints, injects context, 
        and prepares it for the LLM Twin execution.
        """
        if not self.db.client:
            return {}

        res = self.db.client.table("task_blueprints").select("payload_template").eq("task_id", task_name).execute()
        if not res.data:
            print(f"[TASK_ASSEMBLER] No blueprint found for {task_name}")
            return {"error": "Blueprint not found"}
        
        template = res.data[0]["payload_template"]

        # Inject context (Template rendering)
        # e.g., replacing "{{TARGET_DOCUMENT_ID}}" with the actual URL
        template_str = json.dumps(template)
        for key, value in runtime_context.items():
            placeholder = f"{{{{{key.upper()}}}}}"
            template_str = template_str.replace(placeholder, str(value))
        
        final_payload = json.loads(template_str)

        # In a real system, you would pass `final_payload` to your LLM here.
        # For demonstration, we just return the assembled payload.
        print(f"[TASK_ASSEMBLER] Executing task {task_name} with payload: {final_payload}")
        return final_payload
