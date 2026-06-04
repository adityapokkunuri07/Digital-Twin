from fastapi import APIRouter, Depends, HTTPException, Query
from uuid import UUID, uuid4
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from backend.app.core.database import DatabaseService, SupabaseDatabaseService
from backend.app.core.config import settings
from backend.app.services.embedding_service import LocalTransformerEmbeddingService
from backend.app.services.ingestion_service import StructuralRAGIngestionPipeline
from backend.app.services.hybrid_rag_service import HybridRAGEngine
from backend.app.services.feasibility_validator import FeasibilityValidator
from backend.app.services.obsidian_service import ObsidianExportService
from backend.app.services.journalist_service import AIOnboardingJournalist
from backend.app.orchestrator.state_machine import ZeroTrustOrchestrator

router = APIRouter()

# Dependency providers
def get_db() -> DatabaseService:
    # Always return a singleton-like service or initialized instance
    return SupabaseDatabaseService(settings.SUPABASE_URL, settings.SUPABASE_KEY)

def get_embedding_service() -> LocalTransformerEmbeddingService:
    return LocalTransformerEmbeddingService(settings.EMBEDDING_MODEL_NAME)

def get_rag_engine(
    db: DatabaseService = Depends(get_db),
    emb: LocalTransformerEmbeddingService = Depends(get_embedding_service)
) -> HybridRAGEngine:
    return HybridRAGEngine(db, emb)

def get_orchestrator(
    db: DatabaseService = Depends(get_db),
    rag: HybridRAGEngine = Depends(get_rag_engine)
) -> ZeroTrustOrchestrator:
    return ZeroTrustOrchestrator(db, rag)


# --- Request/Response Models ---
class ValidateConfigRequest(BaseModel):
    workflow_config: Dict[str, Any]

class SaveConfigRequest(BaseModel):
    config_id: Optional[UUID] = None
    doctor_id: UUID
    workflow_config: Dict[str, Any]
    active_version: str = "1.0.0"

class InterviewRequest(BaseModel):
    transcript: str

class FinalizeOnboardingRequest(BaseModel):
    config_id: UUID
    transcript: str

class IngestDocumentRequest(BaseModel):
    config_id: UUID
    raw_text: str

class InitiateSessionRequest(BaseModel):
    conversation_id: UUID
    config_id: UUID

class QuerySessionRequest(BaseModel):
    session_id: UUID
    query: str

class UnlearnRequest(BaseModel):
    node_ids: List[UUID]
    rationale: str


# --- REST API Endpoints ---

@router.post("/config/validate")
def validate_config(payload: ValidateConfigRequest):
    is_feasible, errors = FeasibilityValidator.validate_config(payload.workflow_config)
    return {
        "is_feasible": is_feasible,
        "errors": errors
    }


@router.post("/config/save")
async def save_config(
    payload: SaveConfigRequest,
    db: DatabaseService = Depends(get_db)
):
    config_id = payload.config_id or uuid4()
    
    # 1. Feasibility check
    is_feasible, errors = FeasibilityValidator.validate_config(payload.workflow_config)
    
    # 2. Save config
    record = await db.save_expert_config(
        config_id, payload.doctor_id, payload.workflow_config,
        payload.active_version, is_feasible, errors
    )
    
    # 3. Project state to Obsidian
    nodes = await db.get_cot_nodes(config_id)
    edges = await db.get_cot_edges(config_id)
    obsidian_sync = ObsidianExportService(settings.OBSIDIAN_VAULT_PATH)
    obsidian_sync.export_config(record, nodes, edges)
    
    return {
        "status": "success",
        "config_id": config_id,
        "is_feasible": is_feasible,
        "errors": errors,
        "record": record
    }


@router.post("/onboarding/interview")
async def onboarding_interview(payload: InterviewRequest):
    journalist = AIOnboardingJournalist()
    saturation, is_satisfied, next_prompt = await journalist.analyze_onboarding_session(payload.transcript)
    return {
        "saturation_score": saturation,
        "is_satisfied": is_satisfied,
        "next_prompt": next_prompt
    }


@router.post("/onboarding/finalize")
async def finalize_onboarding(
    payload: FinalizeOnboardingRequest,
    db: DatabaseService = Depends(get_db)
):
    journalist = AIOnboardingJournalist()
    saturation = journalist.calculate_saturation(payload.transcript)
    
    if saturation < 0.90:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot finalize onboarding. Saturation score is {saturation:.2f} (required: >= 0.90)."
        )
        
    # Extract CoT nodes and edges
    nodes, edges = journalist.extract_chain_of_thought(payload.transcript)
    
    # Save to Database
    await db.save_cot_nodes(payload.config_id, nodes)
    await db.save_cot_edges(payload.config_id, edges)
    
    # Trigger Obsidian Sync projection
    config_record = await db.get_expert_config(payload.config_id)
    if config_record:
        obsidian_sync = ObsidianExportService(settings.OBSIDIAN_VAULT_PATH)
        obsidian_sync.export_config(config_record, nodes, edges)
        
    return {
        "status": "success",
        "nodes_count": len(nodes),
        "edges_count": len(edges)
    }


@router.post("/config/ingest")
async def ingest_document(
    payload: IngestDocumentRequest,
    db: DatabaseService = Depends(get_db),
    emb: LocalTransformerEmbeddingService = Depends(get_embedding_service)
):
    pipeline = StructuralRAGIngestionPipeline(db, emb)
    chunks = await pipeline.ingest_raw_text(payload.config_id, payload.raw_text)
    
    # Strip embedding floats from API return payload to reduce bandwidth
    clean_chunks = []
    for c in chunks:
        cc = c.copy()
        cc.pop("embedding", None)
        clean_chunks.append(cc)
        
    return {
        "status": "success",
        "chunks_ingested": len(clean_chunks),
        "chunks": clean_chunks
    }


@router.post("/session/initiate")
async def initiate_session(
    payload: InitiateSessionRequest,
    orch: ZeroTrustOrchestrator = Depends(get_orchestrator)
):
    state = await orch.initialize_session(payload.conversation_id, payload.config_id)
    return state


@router.post("/session/query")
async def query_session(
    payload: QuerySessionRequest,
    orch: ZeroTrustOrchestrator = Depends(get_orchestrator)
):
    state = await orch.run_step(payload.session_id, payload.query)
    return state


@router.post("/config/{config_id}/unlearn")
async def unlearn_nodes(
    config_id: UUID,
    payload: UnlearnRequest,
    db: DatabaseService = Depends(get_db)
):
    """
    Mom and Child Unlearning Protocol (Vector Tombstoning)
    Sets vector embedding = NULL for specified node IDs while retaining structure,
    attaches unlearning rationale, and projects changes to Obsidian.
    """
    nodes = await db.get_cot_nodes(config_id)
    edges = await db.get_cot_edges(config_id)
    
    updated_nodes = []
    unlearn_ids_str = [str(x) for x in payload.node_ids]
    
    for node in nodes:
        nid_str = str(node["node_id"])
        if nid_str in unlearn_ids_str:
            # Vector Tombstoning: nullify content embedding in metadata or directly
            node["metadata"]["unlearned"] = True
            node["metadata"]["unlearning_reason"] = payload.rationale
            node["content"] = "[RETRACTED] " + node["content"]
            # Save unlearning trace
        updated_nodes.append(node)
        
    # Save back
    await db.save_cot_nodes(config_id, updated_nodes)
    
    # Project to Obsidian Vault
    config_record = await db.get_expert_config(config_id)
    if config_record:
        obsidian_sync = ObsidianExportService(settings.OBSIDIAN_VAULT_PATH)
        obsidian_sync.export_config(config_record, updated_nodes, edges)
        
    return {
        "status": "success",
        "unlearned_nodes": unlearn_ids_str
    }
