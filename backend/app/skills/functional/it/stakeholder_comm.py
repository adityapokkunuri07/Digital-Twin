"""
stakeholder_comm.py -- SKL_IT_STAKEHOLDER_COMM Functional Skill
=================================================================
Master orchestrator for the Stakeholder Communication Twin.
Calls the sub-skills in sequence:
    1. PersonaTemplate (context assembly)
    2. BriefGenerator (LLM rewriting)
    3. DocxGenerator (document packaging)
    4. EmailDispatcher (delivery)

Refactored into discrete task methods so the workflow engine can:
  - Chain them as individual nodes
  - Insert human gates between any two steps (especially before delivery)
  - Toggle individual tasks on/off

Task Methods:
  1. task_input_decision  — Validates raw technical decision text
  2. task_assemble_context — Assembles template context for each persona
  3. task_generate_briefs — Generates LLM briefs and saves them to DB
  4. task_expert_review   — Mark briefs as pending/ready (human-only gate by default)
  5. task_generate_docx   — Generates DOCX download links via DocxGenerator
  6. task_send_email      — Dispatches emails to stakeholders via EmailDispatcher

The execute() method remains as a backward-compatible wrapper.
"""
from typing import Dict, Any, List
from app.skills.functional.base_skill import BaseFunctionalSkill


class StakeholderCommSkill(BaseFunctionalSkill):
    """
    Orchestrates the full Stakeholder Communication Twin workflow.
    """

    @staticmethod
    def skill_name() -> str:
        return "SKL_IT_STAKEHOLDER_COMM"

    @staticmethod
    def _is_skill_active(skill_name: str) -> bool:
        """Check if a sub-skill is active in the database."""
        try:
            from app.skills.database.session import SessionLocal
            from app.skills.database.models import SkillDefinition
            db = SessionLocal()
            skill = db.query(SkillDefinition).filter(
                SkillDefinition.skill_name == skill_name
            ).first()
            db.close()
            if skill is None:
                return True  # Default to active if not found
            return skill.is_active
        except Exception:
            return True  # Default to active on error

    # ══════════════════════════════════════════════════════════════════════
    # DISCRETE TASK METHODS
    # ══════════════════════════════════════════════════════════════════════

    @staticmethod
    def task_input_decision(state: Dict[str, Any]) -> Dict[str, Any]:
        """Task 1: Validate the technical decision inputs."""
        raw_text = state.get("raw_text", "")
        persona_ids = state.get("persona_ids", [])
        decision_id = state.get("decision_id", "")

        if not raw_text:
            state["error"] = "No technical decision text provided."
        if not persona_ids:
            state["error"] = "No personas selected."

        print(f"[STAKEHOLDER_COMM] Task 1/6 — Input validated for {len(persona_ids)} persona(s)")
        return state

    @staticmethod
    def task_assemble_context(state: Dict[str, Any]) -> Dict[str, Any]:
        """Task 2: Assemble persona prompt context."""
        if state.get("error"):
            return state

        from app.services.persona_engine import PersonaEngine
        engine = PersonaEngine()
        persona_ids = state.get("persona_ids", [])
        assembled_personas = []

        for pid in persona_ids:
            persona = engine.get_persona(pid)
            if not persona:
                print(f"[STAKEHOLDER_COMM] Persona {pid} not found")
                continue

            # Check if template sub-skill is active
            if StakeholderCommSkill._is_skill_active("SKL_IT_PERSONA_TEMPLATE"):
                # GAP 5: Emulation Precision Guardrail
                # Ensure we have high-confidence context for this persona
                # If not, pause the workflow instead of guessing
                prompt_context = engine.assemble_prompt_context(persona)
                
                # We simulate checking a confidence score from the embedding engine
                # In a real scenario, this would come from the RAG search results
                confidence_score = persona.get("latest_context_confidence", 1.0)
                
                if confidence_score < 0.70:
                    print(f"[STAKEHOLDER_COMM] Low confidence ({confidence_score}) for {persona.get('name')}. Pausing workflow.")
                    state["task_skipped"] = True
                    state["requires_human_context"] = True
                    state["error"] = f"Insufficient historical context for {persona.get('name')} to accurately emulate their tone and priorities. Please provide explicit guidance."
                    # We continue to let the gate catch it
                    return state
                
                persona["assembled_context"] = prompt_context
                print(f"[STAKEHOLDER_COMM] Context assembled for {persona.get('name')}")
            else:
                persona["assembled_context"] = None
                print(f"[STAKEHOLDER_COMM] SKL_IT_PERSONA_TEMPLATE is OFF -- using generic defaults")

            assembled_personas.append(persona)

        state["personas"] = assembled_personas
        print(f"[STAKEHOLDER_COMM] Task 2/6 — Assembled contexts for {len(assembled_personas)} personas")
        return state

    @staticmethod
    def task_generate_briefs(state: Dict[str, Any]) -> Dict[str, Any]:
        """Task 3: Generate LLM briefs and insert as pending into database."""
        if state.get("error"):
            return state

        from app.services.brief_generator import BriefGenerator
        from app.services.supabase_client import SupabaseService

        db = SupabaseService()
        generator = BriefGenerator()
        raw_text = state.get("raw_text", "")
        decision_id = state.get("decision_id", "")
        personas = state.get("personas", [])
        results = []

        for persona in personas:
            pid = persona.get("id")
            persona_name = persona.get("name", "Unknown")

            brief_text = generator.generate_brief(raw_text, persona)
            print(f"[STAKEHOLDER_COMM] Brief generated for {persona_name} ({len(brief_text)} chars)")

            record = {
                "decision_id": decision_id,
                "persona_id": pid,
                "original_content": brief_text,
                "edited_content": "",
                "status": "pending",
                "docx_url": "",
            }

            try:
                save_result = db.client.table("generated_briefs").insert(record).execute()
                brief_record = save_result.data[0] if save_result.data else record
            except Exception as e:
                print(f"[STAKEHOLDER_COMM] DB save failed for {persona_name}: {e}")
                brief_record = record

            brief_record["persona_name"] = persona_name
            brief_record["recipient_email"] = persona.get("recipient_email", "")
            results.append(brief_record)

        state["briefs"] = results
        state["status"] = "briefs_generated"
        print(f"[STAKEHOLDER_COMM] Task 3/6 — Generated and saved {len(results)} brief(s)")
        return state

    @staticmethod
    def task_expert_review(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Task 4: Expert review gate.
        In a synchronous pipeline execution, this is a pass-through that marks briefs as 'under_review'.
        When running as a workflow node, a Human Gate pauses before or after this node.
        """
        if state.get("error"):
            return state

        # In backward compatible / inline modes, we just advance status
        print(f"[STAKEHOLDER_COMM] Task 4/6 — Expert review completed/passed through")
        return state

    @staticmethod
    def task_generate_docx(state: Dict[str, Any]) -> Dict[str, Any]:
        """Task 5: Generate DOCX files for all approved briefs (if skill active)."""
        if state.get("error"):
            return state

        if not StakeholderCommSkill._is_skill_active("SKL_IT_DOCX_GENERATOR"):
            print(f"[STAKEHOLDER_COMM] Task 5/6 — SKL_IT_DOCX_GENERATOR is disabled, skipping")
            return state

        from app.skills.functional.it.docx_generator import DocxGeneratorSkill
        briefs = state.get("briefs", [])
        decision_title = state.get("decision_title", "")
        decision_id = state.get("decision_id", "unknown")

        updated_briefs = []
        for brief in briefs:
            # We build the docx from the edited_content if available, otherwise original_content
            content = brief.get("edited_content") or brief.get("original_content", "")
            persona_name = brief.get("persona_name", "Stakeholder")

            if content:
                docx_res = DocxGeneratorSkill.execute({
                    "brief_text": content,
                    "persona_name": persona_name,
                    "decision_id": decision_id,
                    "decision_title": decision_title
                })
                if "docx_url" in docx_res:
                    brief["docx_url"] = docx_res["docx_url"]
                    # Update in DB as well
                    try:
                        from app.services.supabase_client import SupabaseService
                        db = SupabaseService()
                        db.client.table("generated_briefs").update({
                            "docx_url": docx_res["docx_url"]
                        }).eq("id", brief.get("id")).execute()
                    except Exception as e:
                        print(f"[STAKEHOLDER_COMM] Failed to update DOCX URL in DB: {e}")

            updated_briefs.append(brief)

        state["briefs"] = updated_briefs
        print(f"[STAKEHOLDER_COMM] Task 5/6 — DOCX packaging complete")
        return state

    @staticmethod
    def task_send_email(state: Dict[str, Any]) -> Dict[str, Any]:
        """Task 6: Send generated briefs to recipients (if skill active)."""
        if state.get("error"):
            return state

        if not StakeholderCommSkill._is_skill_active("SKL_IT_EMAIL_DISPATCHER"):
            print(f"[STAKEHOLDER_COMM] Task 6/6 — SKL_IT_EMAIL_DISPATCHER is disabled, skipping")
            return state

        from app.skills.functional.it.email_dispatcher import EmailDispatcherSkill
        briefs = state.get("briefs", [])

        email_results = []
        for brief in briefs:
            recipient = brief.get("recipient_email", "")
            content = brief.get("edited_content") or brief.get("original_content", "")
            persona_name = brief.get("persona_name", "Stakeholder")

            if recipient and content:
                email_res = EmailDispatcherSkill.execute({
                    "recipient_email": recipient,
                    "subject": "Architecture Decision Brief",
                    "body_text": content,
                    "persona_name": persona_name,
                    "docx_url": brief.get("docx_url", "")
                })
                email_results.append(email_res)

        state["email_results"] = email_results
        state["status"] = "delivered"
        print(f"[STAKEHOLDER_COMM] Task 6/6 — Email delivery complete")
        return state

    # ══════════════════════════════════════════════════════════════════════
    # BACKWARD-COMPATIBLE EXECUTE (calls tasks in sequence)
    # ══════════════════════════════════════════════════════════════════════

    @staticmethod
    def execute(payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Full Stakeholder Communication pipeline.
        Runs Tasks 1 to 3, then stops (returning pending briefs for expert review).
        This matches the original backward-compatible behavior.
        """
        state = {
            "decision_id": payload.get("decision_id", ""),
            "raw_text": payload.get("raw_text", ""),
            "persona_ids": payload.get("persona_ids", []),
            "decision_title": payload.get("decision_title", ""),
        }

        print(f"\n{'='*60}")
        print(f"[STAKEHOLDER_COMM] Starting pipeline for {len(state['persona_ids'])} persona(s)")
        print(f"{'='*60}\n")

        state = StakeholderCommSkill.task_input_decision(state)
        if state.get("error"):
            return {"error": state["error"]}

        state = StakeholderCommSkill.task_assemble_context(state)
        state = StakeholderCommSkill.task_generate_briefs(state)
        state = StakeholderCommSkill.task_expert_review(state)

        # In backward compatible execute, we don't automatically generate docx and email,
        # because the original skill returned a pending status and waited for approval.
        # However, we allow subsequent pipeline nodes to run task_generate_docx and task_send_email.

        print(f"\n{'='*60}")
        print(f"[STAKEHOLDER_COMM] Pipeline complete. {len(state.get('briefs', []))} brief(s) generated.")
        print(f"{'='*60}\n")

        return {
            "decision_id": state.get("decision_id"),
            "briefs": state.get("briefs"),
            "total": len(state.get("briefs", [])),
            "status": "briefs_generated",
        }

    @staticmethod
    def describe_result(result: Dict[str, Any]) -> str:
        if "error" in result:
            return f"Stakeholder Communication failed: {result['error']}"
        total = result.get("total", 0)
        return f"Generated {total} stakeholder brief(s). Review and approve them to trigger delivery."
