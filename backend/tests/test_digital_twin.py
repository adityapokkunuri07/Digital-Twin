import pytest
import asyncio
from uuid import UUID, uuid4
from backend.app.core.middleware import PIIAnonymizer
from backend.app.services.feasibility_validator import FeasibilityValidator
from backend.app.services.embedding_service import LocalTransformerEmbeddingService
from backend.app.services.ingestion_service import StructuralRAGIngestionPipeline
from backend.app.services.hybrid_rag_service import HybridRAGEngine
from backend.app.core.database import SupabaseDatabaseService
from backend.app.orchestrator.state_machine import ZeroTrustOrchestrator

@pytest.fixture
def anyio_backend():
    return 'asyncio'

# 1. Test PII Sanitization
def test_pii_sanitization():
    anonymizer = PIIAnonymizer()
    mapping = {}
    
    text = "Contact patient at avery@cardiology.com or call 555-019-2834. SSN: 000-12-3456."
    sanitized = anonymizer.anonymize(text, mapping)
    
    # Check that PII elements were masked
    assert "@" not in sanitized
    assert "555-019-2834" not in sanitized
    assert "000-12-3456" not in sanitized
    
    # Check that tokens exist
    assert "[EMAIL-" in sanitized
    assert "[PHONE-" in sanitized
    assert "[SSN-" in sanitized
    
    # Check rehydration
    rehydrated = anonymizer.de_anonymize(sanitized, mapping)
    assert rehydrated == text


# 2. Test Feasibility Validator
def test_feasibility_validator_valid():
    config = {
        "steps": [
            { "id": "1", "name": "Intake", "inputs": [], "outputs": ["symptoms"], "dependencies": [] },
            { "id": "2", "name": "Evaluation", "inputs": ["symptoms"], "outputs": ["severe"], "dependencies": ["1"] }
        ]
    }
    is_feasible, errors = FeasibilityValidator.validate_config(config)
    assert is_feasible is True
    assert len(errors) == 0

def test_feasibility_validator_cycle():
    config = {
        "steps": [
            { "id": "1", "name": "Intake", "inputs": [], "outputs": [], "dependencies": ["2"] },
            { "id": "2", "name": "Evaluation", "inputs": [], "outputs": [], "dependencies": ["1"] }
        ]
    }
    is_feasible, errors = FeasibilityValidator.validate_config(config)
    assert is_feasible is False
    assert any("Cyclic dependency" in err for err in errors)

def test_feasibility_validator_unresolved_inputs():
    config = {
        "steps": [
            { "id": "1", "name": "Intake", "inputs": ["non_existent_var"], "outputs": [], "dependencies": [] }
        ]
    }
    is_feasible, errors = FeasibilityValidator.validate_config(config)
    assert is_feasible is False
    assert any("requires inputs" in err for err in errors)


# 3. Test Ingestion Pipeline
@pytest.mark.anyio
async def test_ingestion_pipeline():
    db = SupabaseDatabaseService() # Mock mode by default
    emb = LocalTransformerEmbeddingService()
    pipeline = StructuralRAGIngestionPipeline(db, emb)
    
    markdown_content = """# Intake Guidelines
This is a root description.
## Patient Intake Symptoms
Check symptoms.
### Extreme Emergency Cases
Severe chest tightness is checked.
"""
    config_id = uuid4()
    chunks = await pipeline.ingest_raw_text(config_id, markdown_content)
    
    assert len(chunks) >= 3
    # Check ordering sequential
    assert chunks[0]["order_index"] == 0
    assert chunks[1]["order_index"] == 1
    
    # Check parent path extraction
    assert chunks[0]["current_path"] == "intake_guidelines"
    assert chunks[1]["current_path"] == "intake_guidelines.patient_intake_symptoms"
    assert chunks[2]["current_path"] == "intake_guidelines.patient_intake_symptoms.extreme_emergency_cases"
    assert chunks[2]["parent_path"] == "intake_guidelines.patient_intake_symptoms"


# 4. Test Hybrid RAG
@pytest.mark.anyio
async def test_hybrid_rag_gate_and_hydration():
    db = SupabaseDatabaseService()
    emb = LocalTransformerEmbeddingService()
    rag = HybridRAGEngine(db, emb)
    
    config_id = uuid4()
    # Save a fake parent node and child node in mock db
    parent_chunk = {
        "chunk_id": uuid4(),
        "config_id": config_id,
        "order_index": 0,
        "title": "Aortic Dissection Protocol",
        "content": "This is a full guideline document containing details for cardiologists.",
        "parent_path": "",
        "current_path": "cardiology_protocol",
        "tags": ["aorta"],
        "synthetic_questions": ["What is aortic dissection?"],
        "embedding": [0.1] * 384
    }
    child_chunk = {
        "chunk_id": uuid4(),
        "config_id": config_id,
        "order_index": 1,
        "title": "Symptom Triggers",
        "content": "Look for radiating back pain and tearing sensations.",
        "parent_path": "cardiology_protocol",
        "current_path": "cardiology_protocol.symptoms",
        "tags": ["pain"],
        "synthetic_questions": ["What symptoms to watch?"],
        "embedding": [0.2] * 384
    }
    
    await db.save_knowledge_chunks(config_id, [parent_chunk, child_chunk])
    
    # Run retrieval
    context, selected, rejected = await rag.retrieve_context(config_id, "radiating back pain")
    
    # Under mock, combined scores are returning 0.90 (above gate)
    assert len(selected) > 0
    # Verification of parent hydration: context should contain parent content
    assert "This is a full guideline document" in context
    assert "cardiology_protocol" in context


# 5. Test State Machine Node Transitions and Anomaly halts
@pytest.mark.anyio
async def test_state_machine_execution():
    db = SupabaseDatabaseService()
    emb = LocalTransformerEmbeddingService()
    rag = HybridRAGEngine(db, emb)
    orch = ZeroTrustOrchestrator(db, rag)
    
    config_id = uuid4()
    doctor_id = uuid4()
    
    # Save a simple config
    workflow_config = {
        "steps": [
            { "id": "step_1", "name": "Intake Vitals", "inputs": ["temperature"], "outputs": ["evaluation_done"], "dependencies": [] }
        ]
    }
    await db.save_expert_config(config_id, doctor_id, workflow_config, "1.0.0", True, [])
    
    # Seed a high-confidence guideline chunk to pass zero-trust threshold (>0.85)
    guideline_chunk = {
        "chunk_id": uuid4(),
        "config_id": config_id,
        "order_index": 0,
        "title": "Temperature Guideline",
        "content": "Verify temperature vitals. Normal is 98.6. Severe fever is >= 103.0.",
        "parent_path": "",
        "current_path": "temp_guideline",
        "tags": ["fever"],
        "synthetic_questions": ["What is normal temperature?"],
        "embedding": [0.1] * 384
    }
    await db.save_knowledge_chunks(config_id, [guideline_chunk])
    
    # Initialize session
    conv_id = uuid4()
    state = await orch.initialize_session(conv_id, config_id)
    session_id = UUID(state["session_id"])
    
    assert state["current_node"] == "start"
    
    # Step A: Query without required variable 'temperature'
    state = await orch.run_step(session_id, "I feel warm today")
    assert state["current_node"] == "data_gathering"
    assert "temperature" in state["output_message"]
    
    # Step B: Provide normal temperature -> should succeed to action dispatch
    state = await orch.run_step(session_id, "My temperature is 98.6")
    assert state["gathered_data"].get("temperature") == 98.6
    assert state["current_node"] == "action_dispatch"
    
    # Reset session for safety halt test
    state = await orch.initialize_session(conv_id, config_id)
    session_id = UUID(state["session_id"])
    
    # Step C: Provide extreme fever temperature (>= 103.0) -> halts state machine
    state = await orch.run_step(session_id, "My temperature is 103.5")
    assert state["current_node"] == "human_intercept"
    assert state["requires_review"] is True
    assert state["is_paused"] is True
    assert "CRITICAL ESCALATION TRIGGERED" in state["output_message"]
