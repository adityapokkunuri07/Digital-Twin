from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uuid

from backend.app.services.workflow_generator import WorkflowGeneratorService
from backend.app.core.interfaces.repositories import WorkflowRepository, ThresholdRepository
# Ensure we have access to these repos via dependencies
from backend.app.api.dependencies import get_preconsult_repo

router = APIRouter(prefix="/workflows", tags=["Workflows"])

class TaskInput(BaseModel):
    description: str
    actor: str

class WorkflowGenerateRequest(BaseModel):
    workflow_name: str
    config_id: str
    doctor_id: str = "4a8f39b6-89d1-4db8-bbbe-d9616e00b8e2"
    tasks: List[TaskInput]

def get_workflow_generator():
    return WorkflowGeneratorService()

@router.post("/generate")
async def generate_workflow(
    request: WorkflowGenerateRequest,
    generator: WorkflowGeneratorService = Depends(get_workflow_generator),
    repo = Depends(get_preconsult_repo) # We'll reuse the Supabase client from preconsult_repo
):
    try:
        # 1. Map via LLM
        tasks_input = [{"description": t.description, "actor": t.actor} for t in request.tasks]
        result = generator.generate_workflow(tasks_input)
        
        # 2. Check for rejections
        rejections = []
        for i, task in enumerate(result.get("tasks", [])):
            if not task.get("is_supported", True):
                rejections.append({
                    "task_index": i,
                    "description": task.get("original_description"),
                    "reason": task.get("rejection_reason")
                })
                
        if rejections:
            raise HTTPException(status_code=400, detail={"rejections": rejections})
            
        # 3. Save to Supabase
        client = repo.client
        config_id_str = request.config_id
        
        # Create doctor_workflows entry
        wf_res = client.table("doctor_workflows").insert({
            "config_id": config_id_str,
            "workflow_name": request.workflow_name,
            "doctor_id": request.doctor_id
        }).execute()
        
        if not wf_res.data:
            raise HTTPException(status_code=500, detail="Failed to create workflow record")
            
        workflow_id = wf_res.data[0]["id"]
        
        # Insert workflow_tasks
        tasks_to_insert = []
        for i, task in enumerate(result.get("tasks", [])):
            strat_id = task.get("strategy_identifier")
            if strat_id == "GENERAL_INTAKE":
                strat_id = None
                
            assigned_executor = task.get("assigned_executor", "TWIN")
            
            if assigned_executor == "DOCTOR":
                alignment = "human_intercept"
            elif strat_id is not None:
                alignment = "processing"
            else:
                alignment = "data_gathering"
                
            tasks_to_insert.append({
                "workflow_id": workflow_id,
                "step_number": i + 1,
                "task_name": f"Step {i+1}",
                "node_alignment": alignment,
                "strategy_identifier": strat_id,
                "assigned_executor": assigned_executor,
                "task_config": {"required_variables": task.get("required_variables", [])}
            })
            
        if tasks_to_insert:
            client.table("workflow_tasks").insert(tasks_to_insert).execute()
            
        # Insert thresholds
        thresholds_to_insert = []
        for th in result.get("thresholds", []):
            thresholds_to_insert.append({
                "config_id": config_id_str,
                "doctor_id": request.doctor_id,
                "entity_name": th.get("entity_name"),
                "max_allowable_value": th.get("max_allowable_value"),
                "critical_escalation_triggers": th.get("critical_escalation_triggers", [])
            })
            
        if thresholds_to_insert:
            client.table("journalist_entity_thresholds").insert(thresholds_to_insert).execute()
            
        return {"status": "success", "workflow_id": workflow_id, "generated_plan": result}

    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))
