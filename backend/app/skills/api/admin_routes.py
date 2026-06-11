from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.skills.database.session import get_db
from app.skills.database.models import SkillDefinition, ExecutionLog

router = APIRouter()

@router.get("/skills")
def get_skills(db: Session = Depends(get_db)):
    """Fetch all skill definitions for the Guardrail Editor."""
    skills = db.query(SkillDefinition).all()
    # Mock metadata for the UI since DB only stores operational state
    SKILL_META = {
        "SKL_IT_ARCH_DRIFT": {
            "label": "Architecture Drift Detection",
            "type": "functional",
            "description": "Scans IT codebases against approved ADRs to detect architectural drift.",
            "flow": ["Clone Repo", "Filter IT Files", "Extract LLM Snippets", "Compare Rules", "Generate Report"]
        },
        "SKL_IT_BLAST_RADIUS": {
            "label": "Blast Radius Simulator",
            "type": "functional",
            "description": "Intercepts GitHub PRs and simulates cascading failures, circular dependencies and resource cost impact before merge.",
            "flow": ["Receive Webhook", "Read PR Diff", "Map AST", "Profile Infra", "Simulate Blast", "Post GitHub Comment"]
        },
        "SKL_IT_PROJECT_PREDICTION": {
            "label": "Project Velocity Prediction",
            "type": "functional",
            "description": "Predicts sprint delivery risks based on velocity delta and requirement churn.",
            "flow": ["Fetch Metrics", "Analyze Trends", "Predict Delivery"]
        },
        "SKL_IT_STAKEHOLDER_COMM": {
            "label": "Stakeholder Communication Twin",
            "type": "functional",
            "description": "Rewrites technical decisions into audience-specific briefs, packages as DOCX, and delivers via email. Learns the architect's tone over time.",
            "flow": ["Input Decision", "Select Audiences", "Load Personas", "Generate Briefs (LLM)", "Architect Review", "Build DOCX", "Send Email"]
        },
        "SKL_IT_PERSONA_TEMPLATE": {
            "label": "Persona Template Engine",
            "type": "functional",
            "description": "Maintains audience personas (CEO tone, Finance tone, etc.) and learns from architect edits to improve brief quality over time.",
            "flow": ["Load Persona Profile", "Assemble Prompt Context", "Capture Edits", "Update Language Profile"]
        },
        "SKL_IT_DOCX_GENERATOR": {
            "label": "DOCX Builder",
            "type": "functional",
            "description": "Converts approved brief text into a styled one-pager Word document using python-docx.",
            "flow": ["Parse Brief", "Apply Corporate Styling", "Generate DOCX", "Upload to Storage"]
        },
        "SKL_IT_EMAIL_DISPATCHER": {
            "label": "Email Dispatcher",
            "type": "functional",
            "description": "Sends stakeholder briefs via SMTP with optional DOCX file attachment.",
            "flow": ["Resolve Recipient", "Build Email", "Attach DOCX", "Send via SMTP", "Log Delivery"]
        },
        "send_communication": {
            "label": "Send Communication",
            "type": "base",
            "description": "Generic capability to send an email, slack, or SMS notification.",
            "flow": ["Resolve Template", "Inject Vars", "Dispatch"]
        }
    }

    result = []
    for s in skills:
        # Only show IT skills or generic base skills in this view
        if not (s.skill_name.startswith("SKL_IT_") or s.skill_name == "send_communication"):
            continue
            
        meta = SKILL_META.get(s.skill_name, {
            "label": s.skill_name.replace("_", " ").title(),
            "type": "base" if s.skill_name.islower() else "functional",
            "description": "No description provided.",
            "flow": []
        })
        
        result.append({
            "id": s.skill_name, # Frontend uses string id for the code label
            "db_id": s.id,
            "skill_name": s.skill_name,
            "is_active": s.is_active,
            "requires_human_approval": s.requires_human_approval,
            "label": meta["label"],
            "type": meta["type"],
            "description": meta["description"],
            "flow": meta["flow"]
        })
    return result

@router.post("/skills/{skill_name}/toggle")
def toggle_skill(skill_name: str, db: Session = Depends(get_db)):
    """Toggle the is_active status of a skill."""
    skill = db.query(SkillDefinition).filter(SkillDefinition.skill_name == skill_name).first()
    if not skill:
        # If it doesn't exist, create it (mocking initial discovery)
        skill = SkillDefinition(skill_name=skill_name, is_active=True)
        db.add(skill)
    else:
        skill.is_active = not skill.is_active
    
    db.commit()
    db.refresh(skill)
    return {"skill_name": skill.skill_name, "is_active": skill.is_active}

@router.get("/logs")
def get_logs(db: Session = Depends(get_db), limit: int = 50):
    """Fetch recent execution logs for the Audit View."""
    logs = db.query(ExecutionLog).order_by(ExecutionLog.created_at.desc()).limit(limit).all()
    return [
        {
            "id": l.id,
            "workflow_id": l.workflow_id,
            "expert_id": l.expert_id,
            "skill_name": l.skill_name,
            "status": l.status,
            "raw_payload": l.raw_payload,
            "error_trace": l.error_trace,
            "created_at": l.created_at.isoformat() + "Z" if l.created_at else None
        }
        for l in logs
    ]
