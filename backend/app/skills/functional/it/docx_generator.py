"""
docx_generator.py -- SKL_DOCX_GENERATOR Functional Skill
==========================================================
Converts approved brief text into a styled one-pager Word document
using python-docx and uploads to Supabase Storage.

Auto-discovered by skill_router.py -- NO edits to shared files needed.
"""
from typing import Dict, Any
from app.skills.functional.base_skill import BaseFunctionalSkill


class DocxGeneratorSkill(BaseFunctionalSkill):
    """
    Skill that generates DOCX one-pager documents from approved brief text.
    """

    @staticmethod
    def skill_name() -> str:
        return "SKL_IT_DOCX_GENERATOR"

    @staticmethod
    def execute(payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a DOCX document from an approved brief.

        Args (payload):
            brief_text: The approved brief content
            persona_name: Name of the target audience
            decision_id: UUID of the tech decision
            decision_title: Optional title for the header
        """
        from app.services.docx_builder import DocxBuilder

        brief_text = payload.get("brief_text", "")
        persona_name = payload.get("persona_name", "Stakeholder")
        decision_id = payload.get("decision_id", "unknown")
        decision_title = payload.get("decision_title", "")

        if not brief_text:
            return {"error": "No brief_text provided", "docx_url": ""}

        print(f"\n[DOCX_GENERATOR] Generating DOCX for {persona_name}...")

        # Step 1: Build the DOCX file locally
        try:
            local_path = DocxBuilder.build_docx(brief_text, persona_name, decision_title)
        except Exception as e:
            print(f"[DOCX_GENERATOR] Build failed: {e}")
            return {"error": f"DOCX build failed: {str(e)}", "docx_url": ""}

        # Step 2: Upload to Supabase Storage
        docx_url = DocxBuilder.upload_to_storage(local_path, decision_id, persona_name)

        print(f"[DOCX_GENERATOR] Complete. URL: {docx_url}")
        return {
            "docx_url": docx_url,
            "persona_name": persona_name,
            "decision_id": decision_id,
            "status": "generated",
        }

    @staticmethod
    def describe_result(result: Dict[str, Any]) -> str:
        if "error" in result:
            return f"DOCX generation failed: {result['error']}"
        return f"Generated DOCX for {result.get('persona_name', 'unknown')}: {result.get('docx_url', 'N/A')}"
