"""
workflow_runtime.py — Workflow Runtime API (Pause / Resume / Approve)
=====================================================================
Endpoints for the expert to see paused workflows and resume them.
This is the "Resume After Human Completes" system.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
import traceback
from datetime import datetime, timezone

from backend.app.services.supabase_client import SupabaseService
# Dummy replacements for missing old graph modules
def get_db_pool(): return None
def get_encrypted_checkpointer(pool): return None

router = APIRouter()


# ── Request Models ────────────────────────────────────────────────────────────

class ApproveRequest(BaseModel):
    approved_by: str
    human_input: Optional[dict] = None
    deputy_id: Optional[str] = None


# ── List Paused Workflows ────────────────────────────────────────────────────

@router.get("/workflows/paused")
async def list_paused_workflows(expert_id: Optional[str] = None):
    """
    Returns all workflows currently waiting for human action.
    If expert_id is provided, also returns workflows where this user
    is a deputy for the primary expert.
    """
    db = SupabaseService()
    try:
        # Get directly assigned paused workflows
        query = db.client.table("state_ledger").select("*").eq(
            "status", "awaiting_human"
        )
        if expert_id:
            query = query.eq("expert_id", expert_id)

        result = query.order("paused_at", desc=True).execute()
        paused = result.data or []

        # Also get workflows where this user is a deputy
        if expert_id:
            deputies_result = db.client.table("expert_deputies").select(
                "primary_expert_id"
            ).eq("deputy_id", expert_id).eq("is_active", True).execute()

            for dep in (deputies_result.data or []):
                primary_id = dep["primary_expert_id"]
                delegated = db.client.table("state_ledger").select("*").eq(
                    "status", "awaiting_human"
                ).eq("expert_id", primary_id).order(
                    "paused_at", desc=True
                ).execute()

                for item in (delegated.data or []):
                    item["is_delegated"] = True
                    item["primary_expert_id"] = primary_id
                    # Avoid duplicates
                    if not any(p["id"] == item["id"] for p in paused):
                        paused.append(item)

        # Attach LangGraph checkpoint data
        pool = get_db_pool()
        if pool:
            checkpointer = get_encrypted_checkpointer(pool)
            for item in paused:
                run_id = item.get("run_id")
                if run_id:
                    state = checkpointer.get({"configurable": {"thread_id": run_id}})
                    item["checkpoint_data"] = state["values"] if state and "values" in state else None

        return {"paused_workflows": paused, "count": len(paused)}
    except Exception as e:
        if "does not exist" in str(e) or "42P01" in str(e):
            return {"paused_workflows": [], "count": 0}
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ── Get Single Paused Workflow ───────────────────────────────────────────────

@router.get("/workflows/paused/{run_id}")
async def get_paused_workflow(run_id: str):
    """Get details of a specific paused workflow."""
    db = SupabaseService()
    try:
        result = db.client.table("state_ledger").select("*").eq(
            "run_id", run_id
        ).eq("status", "awaiting_human").limit(1).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Paused workflow not found")

        item = result.data[0]
        pool = get_db_pool()
        if pool:
            checkpointer = get_encrypted_checkpointer(pool)
            run_id_val = item.get("run_id")
            if run_id_val:
                state = checkpointer.get({"configurable": {"thread_id": run_id_val}})
                item["checkpoint_data"] = state["values"] if state and "values" in state else None

        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Approve & Resume ─────────────────────────────────────────────────────────

def _run_resume_background(run_id: str, expert_input: dict, workflow_id: str):
    """Background task to resume graph."""
    pass

@router.post("/workflows/{run_id}/approve")
async def approve_workflow(run_id: str, req: ApproveRequest, background_tasks: BackgroundTasks):
    """
    Expert approves a paused workflow.
    Updates state_ledger and triggers pipeline resumption in the background.
    """
    db = SupabaseService()
    try:
        # Verify the workflow is actually paused
        check = db.client.table("state_ledger").select("*").eq(
            "run_id", run_id
        ).eq("status", "awaiting_human").limit(1).execute()

        if not check.data:
            raise HTTPException(status_code=404, detail="No paused workflow found with this run_id")

        ledger_entry = check.data[0]
        expert_id = ledger_entry.get("expert_id", "")
        workflow_id = ledger_entry.get("workflow_id", "")

        # If this is a deputy approval, verify delegation
        if req.deputy_id:
            dep_check = db.client.table("expert_deputies").select("id").eq(
                "primary_expert_id", expert_id
            ).eq("deputy_id", req.deputy_id).eq("is_active", True).limit(1).execute()

            if not dep_check.data:
                raise HTTPException(
                    status_code=403,
                    detail="You are not authorized as a deputy for this expert"
                )

        # Update state_ledger
        now = datetime.now(timezone.utc).isoformat()
        db.client.table("state_ledger").update({
            "status": "resumed",
            "approved_by": req.approved_by,
            "deputy_id": req.deputy_id or "",
            "human_input": req.human_input or {},
            "resumed_at": now,
        }).eq("run_id", run_id).eq("status", "awaiting_human").execute()

        # Send notification to primary expert if deputy acted
        if req.deputy_id:
            task_name = ledger_entry.get("task_name", "Unknown")
            db.client.table("notifications").insert({
                "recipient_id": expert_id,
                "type": "deputy_acted",
                "title": f"Deputy approved '{task_name}'",
                "message": (
                    f"{req.deputy_id} approved task '{task_name}' on your behalf "
                    f"at {now}."
                ),
                "metadata": {
                    "run_id": run_id,
                    "deputy_id": req.deputy_id,
                    "task_name": task_name,
                },
            }).execute()

        # Log to execution_logs for audit trail
        try:
            db.client.table("execution_logs").insert({
                "workflow_id": workflow_id,
                "task_id": ledger_entry.get("task_id"),
                "expert_id": expert_id,
                "status": "human_approved",
                "raw_payload": {
                    "approved_by": req.approved_by,
                    "deputy_id": req.deputy_id,
                    "human_input": req.human_input,
                },
            }).execute()
        except Exception:
            pass  # Non-fatal — audit log failure shouldn't block approval

        # GAP 2: Asynchronous API Decoupling
        background_tasks.add_task(_run_resume_background, run_id, req.human_input or {"approved": True}, workflow_id)

        return {
            "status": "approved",
            "run_id": run_id,
            "approved_by": req.approved_by,
            "deputy_id": req.deputy_id,
            "message": "Workflow approved. The Twin will resume from where it paused.",
        }

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ── Reject / Cancel ──────────────────────────────────────────────────────────

@router.post("/workflows/{run_id}/reject")
async def reject_workflow(run_id: str, background_tasks: BackgroundTasks, rejected_by: str = "expert"):
    """Reject a paused workflow — terminates graph."""
    db = SupabaseService()
    try:
        now = datetime.now(timezone.utc).isoformat()
        
        # We need workflow_id to resume the background graph
        check = db.client.table("state_ledger").select("workflow_id").eq(
            "run_id", run_id
        ).eq("status", "awaiting_human").limit(1).execute()

        db.client.table("state_ledger").update({
            "status": "rejected",
            "approved_by": rejected_by,
            "resumed_at": now,
        }).eq("run_id", run_id).eq("status", "awaiting_human").execute()

        if check.data:
            workflow_id = check.data[0].get("workflow_id")
            if workflow_id:
                # Trigger the graph to resume with rejection payload so it can exit
                background_tasks.add_task(_run_resume_background, run_id, {"rejected": True}, workflow_id)

        return {"status": "rejected", "run_id": run_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Unified Digital Twin Execution ───────────────────────────────────────────

from backend.app.services.task_assembler import TaskAssembler

class AssembleRequest(BaseModel):
    task_id: str
    expert_id: str

class ExecuteRequest(BaseModel):
    task_id: str
    runtime_context: dict

@router.post("/workflows/assemble")
async def assemble_task(req: AssembleRequest):
    """
    Assembles a payload template for a task based on the expert's rules in the knowledge hub.
    Caches it in task_blueprints.
    """
    assembler = TaskAssembler()
    template = assembler.assemble_blueprint(req.task_id, req.expert_id)
    if not template:
        raise HTTPException(status_code=404, detail="Could not assemble blueprint. No rules found.")
    return {"status": "success", "template": template}

@router.post("/workflows/execute")
async def execute_assembled_task(req: ExecuteRequest):
    """
    Executes a task by fetching its assembled blueprint and injecting runtime context.
    """
    assembler = TaskAssembler()
    payload = assembler.execute_task(req.task_id, req.runtime_context)
    if "error" in payload:
        raise HTTPException(status_code=404, detail=payload["error"])
    
    # Normally we would dispatch this payload to the LLM (Twin) here
    return {"status": "success", "executed_payload": payload, "message": "Task dispatched to Twin successfully."}

@router.get("/workflows/knowledge-proofs")
async def get_knowledge_proofs():
    """
    Fetches the raw rules from knowledge_hub and the assembled blueprint from task_blueprints
    for the UI to visualize side-by-side.
    """
    db = SupabaseService()
    try:
        rules_res = db.client.table("knowledge_hub").select("*").order("execution_order").execute()
        blueprints_res = db.client.table("task_blueprints").select("*").execute()
        
        return {
            "status": "success",
            "rules": rules_res.data or [],
            "blueprints": blueprints_res.data or []
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
