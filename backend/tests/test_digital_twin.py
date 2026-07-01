"""
Digital Twin — Test Suite

Tests are organized by SOLID component:
1. PII Sanitization (Middleware)
2. Feasibility Validator (Service)
3. Ingestion Pipeline (Service + KnowledgeRepository)
4. Hybrid RAG (Service + KnowledgeRepository)
5. State Machine (Orchestrator + Extractors + Safety Rules)

All tests use segregated repository interfaces for clean dependency injection.
"""
import pytest
import warnings
from uuid import UUID, uuid4

# Core imports
from backend.app.core.middleware import PIIAnonymizer
from backend.app.services.feasibility_validator import FeasibilityValidator

# New segregated repositories
from backend.app.repositories.supabase_config_repo import SupabaseConfigRepository
from backend.app.repositories.supabase_knowledge_repo import SupabaseKnowledgeRepository
from backend.app.repositories.supabase_session_repo import SupabaseSessionRepository

# New embedding location
from backend.app.services.embedding.local_transformer import LocalTransformerEmbeddingService

# Services
from backend.app.services.ingestion_service import StructuralRAGIngestionPipeline
from backend.app.services.hybrid_rag_service import HybridRAGEngine

# Orchestrator + pluggable components
from backend.app.orchestrator.state_machine import ZeroTrustOrchestrator
from backend.app.verticals.healthcare.extractors.vitals_extractor import VitalsExtractor
from backend.app.verticals.healthcare.extractors.symptom_extractor import SymptomExtractor
from backend.app.verticals.healthcare.safety_rules.fever_rule import FeverSafetyRule
from backend.app.verticals.healthcare.safety_rules.cardiac_rule import CardiacSafetyRule
from backend.app.orchestrator.safety_rules.confidence_rule import ConfidenceSafetyRule


@pytest.fixture
def anyio_backend():
    return "asyncio"


# ─── 1. Test PII Sanitization ────────────────────────────────────────

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


# ─── 2. Test Feasibility Validator ────────────────────────────────────

def test_feasibility_validator_valid():
    config = {
        "steps": [
            {"id": "1", "name": "Intake", "inputs": [], "outputs": ["symptoms"], "dependencies": []},
            {"id": "2", "name": "Evaluation", "inputs": ["symptoms"], "outputs": ["severe"], "dependencies": ["1"]},
        ]
    }
    is_feasible, errors = FeasibilityValidator.validate_config(config)
    assert is_feasible is True
    assert len(errors) == 0


def test_feasibility_validator_cycle():
    config = {
        "steps": [
            {"id": "1", "name": "Intake", "inputs": [], "outputs": [], "dependencies": ["2"]},
            {"id": "2", "name": "Evaluation", "inputs": [], "outputs": [], "dependencies": ["1"]},
        ]
    }
    is_feasible, errors = FeasibilityValidator.validate_config(config)
    assert is_feasible is False
    assert any("Cyclic dependency" in err for err in errors)


def test_feasibility_validator_unresolved_inputs():
    config = {
        "steps": [
            {"id": "1", "name": "Intake", "inputs": ["non_existent_var"], "outputs": [], "dependencies": []},
        ]
    }
    is_feasible, errors = FeasibilityValidator.validate_config(config)
    assert is_feasible is False
    assert any("requires inputs" in err for err in errors)


# ─── 3. Test Ingestion Pipeline (KnowledgeRepository) ────────────────

@pytest.mark.anyio
async def test_ingestion_pipeline():
    knowledge_repo = SupabaseKnowledgeRepository()  # Mock mode
    emb = LocalTransformerEmbeddingService()
    pipeline = StructuralRAGIngestionPipeline(knowledge_repo, emb)

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
    assert chunks[0]["order_index"] == 0
    assert chunks[1]["order_index"] == 1

    # Check parent path extraction
    assert chunks[0]["current_path"] == "intake_guidelines"
    assert chunks[1]["current_path"] == "intake_guidelines.patient_intake_symptoms"
    assert chunks[2]["current_path"] == "intake_guidelines.patient_intake_symptoms.extreme_emergency_cases"
    assert chunks[2]["parent_path"] == "intake_guidelines.patient_intake_symptoms"


# ─── 4. Test Hybrid RAG (KnowledgeRepository) ────────────────────────

@pytest.mark.anyio
async def test_hybrid_rag_gate_and_hydration():
    knowledge_repo = SupabaseKnowledgeRepository()  # Mock mode
    emb = LocalTransformerEmbeddingService()
    rag = HybridRAGEngine(knowledge_repo, emb)

    config_id = uuid4()

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
        "embedding": [0.1] * 384,
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
        "embedding": [0.2] * 384,
    }

    await knowledge_repo.save_knowledge_chunks(config_id, [parent_chunk, child_chunk])

    context, selected, rejected = await rag.retrieve_context(config_id, "radiating back pain")

    assert len(selected) > 0
    assert "This is a full guideline document" in context
    assert "cardiology_protocol" in context


# ─── 5. Test State Machine (Orchestrator + Extractors + Safety Rules) ─

@pytest.mark.skip(reason="Needs update for V2 initialization flow")
@pytest.mark.anyio
async def test_state_machine_execution():
    config_repo = SupabaseConfigRepository()  # Mock mode
    session_repo = SupabaseSessionRepository()  # Mock mode
    knowledge_repo = SupabaseKnowledgeRepository()  # Mock mode
    emb = LocalTransformerEmbeddingService()
    rag = HybridRAGEngine(knowledge_repo, emb)

    # Inject pluggable extractors and safety rules
    extractors = [VitalsExtractor(), SymptomExtractor()]
    safety_rules = [
        FeverSafetyRule(),
        CardiacSafetyRule(),
        ConfidenceSafetyRule(confidence_gate=0.85),
    ]

    orch = ZeroTrustOrchestrator(
        config_repo=config_repo,
        session_repo=session_repo,
        rag_engine=rag,
        extractors=extractors,
        safety_rules=safety_rules,
    )

    config_id = uuid4()
    expert_id = uuid4()

    workflow_config = {
        "steps": [
            {"id": "step_1", "name": "Intake Vitals", "inputs": ["temperature"], "outputs": ["evaluation_done"], "dependencies": []},
        ]
    }
    await config_repo.save_expert_config(config_id, expert_id, workflow_config, "1.0.0", True, [])

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
        "embedding": [0.1] * 384,
    }
    await knowledge_repo.save_knowledge_chunks(config_id, [guideline_chunk])

    # Initialize session
    # conv_id = uuid4()
    # state = await orch.initialize_session(conv_id, config_id)
    # assert state["current_node"] == "data_gathering"
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
    assert "CRITICAL ESCALATION TRIGGERED" in state["output_message"]

@pytest.mark.anyio
async def test_probing_node_routing():
    config_repo = SupabaseConfigRepository()  # Mock mode
    session_repo = SupabaseSessionRepository()  # Mock mode
    knowledge_repo = SupabaseKnowledgeRepository()  # Mock mode
    emb = LocalTransformerEmbeddingService()
    rag = HybridRAGEngine(knowledge_repo, emb)

    orch = ZeroTrustOrchestrator(
        config_repo=config_repo,
        session_repo=session_repo,
        rag_engine=rag,
        extractors=[],
        safety_rules=[],
    )

    config_id = uuid4()
    session_id = uuid4()
    
    # Mock an active session in probing state
    state = {
        "session_id": str(session_id),
        "conversation_id": str(uuid4()),
        "config_id": str(config_id),
        "current_node": "probing",
        "is_paused": False,
        "requires_review": False,
        "classification_score": 1.0,
        "history": []
    }
    
    await session_repo.save_active_session(
        session_id, UUID(state["conversation_id"]), config_id,
        state["current_node"], state, state["is_paused"], state["requires_review"]
    )

    # 1. Test ambiguous query (stay in probing)
    updated_state = await orch.run_step(session_id, "I need some advice")
    assert updated_state["current_node"] == "probing"
    assert "Could you provide a bit more detail" in updated_state["output_message"]

    # 2. Test Q&A query
    updated_state = await orch.run_step(session_id, "How does this work?")
    assert updated_state["current_node"] == "probing"
    assert "clinical assistant" in updated_state["output_message"]
    
    # 3. Test Medical query (advances to data_gathering and sets workflow_id)
    updated_state = await orch.run_step(session_id, "I have a severe stomach pain")
    assert updated_state["current_node"] == "data_gathering"
    assert updated_state["workflow_id"] == "pre_consultation"

