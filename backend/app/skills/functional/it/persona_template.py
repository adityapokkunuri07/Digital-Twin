"""
persona_template.py -- SKL_PERSONA_TEMPLATE Functional Skill
==============================================================
Maintains audience personas (CEO tone, Finance tone, etc.),
assembles prompt context for the LLM, and handles Twin Learning.

Auto-discovered by skill_router.py -- NO edits to shared files needed.
"""
from typing import Dict, Any
from app.skills.functional.base_skill import BaseFunctionalSkill


class PersonaTemplateSkill(BaseFunctionalSkill):
    """
    Skill that manages persona templates and the twin learning loop.
    """

    @staticmethod
    def skill_name() -> str:
        return "SKL_IT_PERSONA_TEMPLATE"

    @staticmethod
    def execute(payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Operations:
            action: "list" | "get" | "create" | "update" | "delete" | "assemble" | "learn"
        """
        from app.services.persona_engine import PersonaEngine

        engine = PersonaEngine()
        action = payload.get("action", "list")

        if action == "list":
            personas = engine.list_personas(active_only=payload.get("active_only", True))
            return {"personas": personas, "count": len(personas)}

        elif action == "get":
            persona = engine.get_persona(payload["persona_id"])
            return {"persona": persona}

        elif action == "create":
            persona = engine.create_persona(
                name=payload["name"],
                language_profile=payload.get("language_profile", ""),
                priorities=payload.get("priorities", ""),
                recipient_email=payload.get("recipient_email", ""),
            )
            return {"persona": persona, "status": "created"}

        elif action == "update":
            updated = engine.update_persona(payload["persona_id"], payload.get("updates", {}))
            return {"persona": updated, "status": "updated"}

        elif action == "delete":
            engine.delete_persona(payload["persona_id"])
            return {"status": "deleted"}

        elif action == "assemble":
            persona = engine.get_persona(payload["persona_id"])
            if not persona:
                return {"error": "Persona not found"}
            context = engine.assemble_prompt_context(persona)
            return {"prompt_context": context, "persona_name": persona["name"]}

        elif action == "learn":
            engine.learn_from_edit(
                persona_id=payload["persona_id"],
                original_content=payload["original_content"],
                edited_content=payload["edited_content"],
            )
            return {"status": "learning_applied"}

        return {"error": f"Unknown action: {action}"}

    @staticmethod
    def describe_result(result: Dict[str, Any]) -> str:
        if "error" in result:
            return f"Persona Template error: {result['error']}"
        if "personas" in result:
            return f"Found {result['count']} persona(s)."
        if "status" in result:
            return f"Persona operation: {result['status']}"
        return "Persona Template operation completed."
