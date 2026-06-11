"""
it.py — IT Domain Skill Payload Schemas
=========================================
All Pydantic models for IT-specific skills live here.
Dev B (IT) owns this file.

ADDING A NEW IT SKILL:
    1. Define the payload schema class below
    2. Register it in the IT_SKILL_REGISTRY dict at the bottom
    3. Create the functional skill in skills/functional/it/
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime
from uuid import UUID


# ── Base Skills (IT) ──────────────────────────────────────────────────────────

class SendCommunicationPayload(BaseModel):
    """Generic communication dispatch — shared across domains but owned by IT for now."""
    template_id: str
    recipient_address: str = Field(description="Email or WhatsApp number")
    dynamic_vars: dict = Field(default_factory=dict, description="Variables for the template")


# ── Functional Skills (IT) ────────────────────────────────────────────────────
class SklItProjectPredictionPayload(BaseModel):
    project_id: UUID
    
    # Execution Metrics
    velocity_delta: float = Field(..., description="Change in team velocity vs previous sprint (%)")
    requirement_churn: float = Field(..., description="Percentage of requirements changed mid-sprint")
    dependency_lag_days: int = Field(default=0, description="Total days stalled due to external dependencies")
    
    # Deep Metrics
    qa_failure_rate: float = Field(default=0.05, description="Percentage of tickets failing QA on first pass")
    documentation_completeness: float = Field(default=0.8, description="0 to 1 score of technical documentation readiness")
    team_burnout_risk: float = Field(default=0.1, description="0 to 1 score based on overtime and sentiment")


class SklItArchDriftPayload(BaseModel):
    """Payload for IT Architecture Drift Detection skill."""
    repo_url: Optional[str] = Field(default=None, description="Direct GitHub repo URL (optional if repo_label given)")
    repo_label: Optional[str] = Field(default=None, description="Label of a registered monitored repo")
    branch: str = Field(default="main", description="Git branch to scan")
    trigger_type: str = Field(default="manual", description="How the scan was triggered: 'manual' | 'chat'")



class SklItBlastRadiusPayload(BaseModel):
    """Payload for PR Blast Radius Simulation skill."""
    repo_owner: str = Field(..., description="GitHub repo owner, e.g. 'acme-corp'")
    repo_name: str  = Field(..., description="GitHub repo name, e.g. 'backend-api'")
    pr_number: int  = Field(..., description="The Pull Request number to simulate")
    owner_id: str   = Field(default="architect", description="Client ID for PAT lookup")


class SklItStakeholderCommPayload(BaseModel):
    """Payload for Stakeholder Communication Twin skill."""
    decision_id: str = Field(..., description="UUID of the saved tech decision")
    raw_text: str = Field(..., description="The raw technical decision text")
    persona_ids: List[str] = Field(..., description="List of persona UUIDs to generate briefs for")
    decision_title: str = Field(default="", description="Optional title for the document header")


class SklItPersonaTemplatePayload(BaseModel):
    """Payload for Persona Template Engine skill."""
    action: str = Field(..., description="Operation: list | get | create | update | delete | assemble | learn")
    persona_id: Optional[str] = Field(default=None, description="Persona UUID (for get/update/delete/assemble/learn)")
    name: Optional[str] = Field(default=None, description="Persona name (for create)")
    language_profile: Optional[str] = Field(default=None, description="Tone instructions")
    priorities: Optional[str] = Field(default=None, description="What they care about")
    recipient_email: Optional[str] = Field(default=None, description="Email address")
    original_content: Optional[str] = Field(default=None, description="Original LLM output (for learn)")
    edited_content: Optional[str] = Field(default=None, description="Architect edited version (for learn)")
    updates: Optional[dict] = Field(default=None, description="Fields to update (for update)")
    active_only: bool = Field(default=True, description="Filter active only (for list)")


class SklItDocxGeneratorPayload(BaseModel):
    """Payload for DOCX Generator skill."""
    brief_text: str = Field(..., description="The approved brief content")
    persona_name: str = Field(default="Stakeholder", description="Name of the target audience")
    decision_id: str = Field(default="unknown", description="UUID of the tech decision")
    decision_title: str = Field(default="", description="Optional title for the document header")


class SklItEmailDispatcherPayload(BaseModel):
    """Payload for Email Dispatcher skill."""
    recipient_email: str = Field(..., description="Target email address")
    subject: str = Field(default="Architecture Decision Brief", description="Email subject")
    body_text: str = Field(..., description="The brief content as email body")
    persona_name: str = Field(default="Stakeholder", description="Name of the audience")
    docx_path: str = Field(default="", description="Optional local path to DOCX for attachment")


# ── IT Skill Registry ─────────────────────────────────────────────────────────
# Maps skill_name -> payload schema for this domain.
# The central validation.py merges all domain registries automatically.

IT_SKILL_REGISTRY = {
    "send_communication": SendCommunicationPayload,
    "SKL_IT_PROJECT_PREDICTION": SklItProjectPredictionPayload,
    "SKL_IT_ARCH_DRIFT": SklItArchDriftPayload,
    "SKL_IT_BLAST_RADIUS": SklItBlastRadiusPayload,
    "SKL_IT_STAKEHOLDER_COMM": SklItStakeholderCommPayload,
    "SKL_IT_PERSONA_TEMPLATE": SklItPersonaTemplatePayload,
    "SKL_IT_DOCX_GENERATOR": SklItDocxGeneratorPayload,
    "SKL_IT_EMAIL_DISPATCHER": SklItEmailDispatcherPayload,
}
