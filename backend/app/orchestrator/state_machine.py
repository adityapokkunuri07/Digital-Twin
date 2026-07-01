"""
Zero-Trust Orchestrator — LangGraph 4-Node State Machine (V2).

Refactored to implement the Zero-Trust Execution architecture from the Engineering Specification:
- Node 1: Data Gathering (Hydration + Prompt Containment + Knowledge Saturation Gate)
- Node 2: Data Processing (Dynamic Dispatch via StrategyRegistry)
- Node 3: Human Intercept (Dynamic Threshold Rule Evaluation)
- Node 4: Action Dispatch

Relies on Immutable Configuration Snapshots inside the AgentState.
"""
from typing import TypedDict, Dict, Any, List
from uuid import UUID, uuid4
import logging

from backend.app.core.interfaces.repositories import ConfigRepository, SessionRepository
from backend.app.core.enums import SessionStatus
from backend.app.services.hybrid_rag_service import HybridRAGEngine
from backend.app.services.llm.gemini_llm import GeminiLLMService
from backend.app.orchestrator.extractors.base import DataExtractor
from backend.app.orchestrator.safety_rules.base import SafetyRule
from backend.app.core.interfaces.embedding import EmbeddingService
from backend.app.orchestrator.confidence_gate import KnowledgeSaturationGate
from backend.app.orchestrator.strategies.registry import StrategyRegistry
from backend.app.services.context_synthesizer import ContextSynthesizer
from backend.app.orchestrator.probing_router import ProbingRouter

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """Typed state schema for the LangGraph execution thread."""
    session_id: str
    conversation_id: str
    config_id: str
    workflow_id: str
    current_step_index: int
    assigned_actor: str
    session_status: str
    current_node: str
    user_query: str
    extracted_telemetry: Dict[str, Any]
    configuration_snapshot: Dict[str, Any]
    retrieved_context: str
    output_message: str
    requires_review: bool
    is_paused: bool
    classification_score: float
    history: List[Dict[str, Any]]
    expert_override_message: str
    end_user_consent_granted: bool
    pending_action: str


class ZeroTrustOrchestrator:
    def __init__(
        self,
        config_repo: ConfigRepository,
        session_repo: SessionRepository,
        rag_engine: HybridRAGEngine,
        llm_service: GeminiLLMService | None = None,
        extractors: List[DataExtractor] | None = None,
        safety_rules: List[SafetyRule] | None = None,
    ):
        self._config_repo = config_repo
        self._session_repo = session_repo
        self._rag_engine = rag_engine
        self._llm_service = llm_service
        self._extractors = extractors or []
        self._safety_rules = safety_rules or []
        self._embedding_service: EmbeddingService | None = None
        self._preconsult_repo = None
        self._saturation_gate = KnowledgeSaturationGate()
        
    def set_preconsult_dependencies(self, preconsult_repo, embedding_service):
        self._preconsult_repo = preconsult_repo
        self._embedding_service = embedding_service

    async def run_step(self, session_id: UUID, user_query: str) -> Dict[str, Any]:
        """
        Execute a single transition step in the V2 4-node state machine.
        """
        # 1. Load session checkpoint (in V2, PreConsultService manages the primary DB state, 
        # but this method still operates on the generic Graph state if called directly)
        session_record = await self._session_repo.get_active_session(session_id)
        if not session_record:
            raise ValueError(f"Session '{session_id}' not found.")

        state: AgentState = session_record["graph_state"]
        state["user_query"] = user_query

        # Node 0: Probing (Dynamic Workflow Determination)
        if state.get("current_node", "probing") == "probing":
            probing_router = ProbingRouter(self._llm_service)
            workflow_id, clarification_msg = probing_router.determine_workflow(user_query)
            
            if workflow_id == "clarify":
                # Stay in probing node
                state["output_message"] = clarification_msg
                await self._save_state(session_id, state)
                return state
            
            if workflow_id == "qa":
                # Handle generic Q&A without advancing to a structured workflow
                context, _, _ = await self._rag_engine.retrieve_context(UUID(state["config_id"]), user_query)
                state["output_message"] = "I am a clinical assistant. I can help assess your symptoms."
                await self._save_state(session_id, state)
                return state
                
            # If we reach here, we found a structured workflow (e.g., 'pre_consultation')
            state["workflow_id"] = workflow_id
            state["current_node"] = "data_gathering"
            # In a real implementation, we would load the 'workflow_id' specific tasks into the configuration_snapshot here
            # For now, the pre-consultation workflow is already loaded in start_session.

        # Lock check
        if state.get("is_paused", False) or state.get("requires_review", False):
            state["output_message"] = "This session has been suspended and is awaiting expert human review."
            return state

        # Read the immutable snapshot
        snapshot = state.get("configuration_snapshot", {})
        tasks = snapshot.get("tasks", [])
        thresholds = snapshot.get("thresholds", [])
        
        current_step_index = state.get("current_step_index", 0)
        if current_step_index >= len(tasks):
            state["output_message"] = "Session completed."
            return state
            
        current_task = tasks[current_step_index]
        assigned_executor = current_task.get("assigned_executor", "TWIN")
        
        # Node Routing
        if assigned_executor == "DOCTOR":
            # Bypass AI Execution -> Route to Node 3 (Human Intercept)
            state["current_node"] = "human_intercept"
            state["requires_review"] = True
            state["is_paused"] = True
            state["session_status"] = SessionStatus.AWAITING_EXPERT_INTERVENTION
            state["output_message"] = "This step requires expert review. You have been placed in the review queue."
            await self._save_state(session_id, state)
            return state

        # ---- NODE 1: DATA GATHERING ----
        state["current_node"] = "data_gathering"
        
        # Execute basic extractors
        text = user_query.lower()
        extracted_any = False
        if "extracted_telemetry" not in state:
            state["extracted_telemetry"] = {}
            
        for extractor in self._extractors:
            extracted = extractor.extract(text)
            if extracted:
                state["extracted_telemetry"].update(extracted)
                extracted_any = True

        expected_schema = current_task.get("task_config", {}).get("required_variables", [])
        
        chat_history = ""
        if self._preconsult_repo:
            logs = await self._preconsult_repo.get_interaction_logs(session_id)
            chat_history = "\n".join([f"{log['sender']}: {log['message_text']}" for log in logs[-5:]])

        # LLM EXTRACTION (Replacing redundant preconsult LLM loop)
        if self._llm_service and not self._llm_service.use_fallback:
            extracted_llm = self._llm_service.extract_variables(text, expected_schema, chat_history)
            if extracted_llm:
                state["extracted_telemetry"].update(extracted_llm)

        # RAG / Schema Hydration (Strict Prompt Containment)
        context, selected_chunks, rejected = await self._rag_engine.retrieve_context(
            UUID(state["config_id"]), user_query
        )
        # Limit to top 3 chunks
        selected_chunks = selected_chunks[:3]
        state["retrieved_context"] = context
        
        # Evaluate Saturation
        conf_score, should_transition = self._saturation_gate.evaluate(
            expected_schema, state["extracted_telemetry"]
        )
        state["classification_score"] = conf_score
        
        if not should_transition:
            # Stay in Node 1
            if self._llm_service and not self._llm_service.use_fallback:
                missing = [v for v in expected_schema if v not in state["extracted_telemetry"]]
                state["output_message"] = self._llm_service.generate_followup(
                    missing, state["extracted_telemetry"], chat_history
                )
            else:
                state["output_message"] = f"Please tell me more about: {expected_schema}"
            await self._save_state(session_id, state)
            return state

        # ---- NODE 2: DATA PROCESSING ----
        state["current_node"] = "processing"
        strategy_id = current_task.get("strategy_identifier")
        escalations = []
        
        if strategy_id and strategy_id != "GENERAL_INTAKE":
            try:
                strategy = StrategyRegistry.resolve(strategy_id)
                # Dispatch execution dynamically
                processed_data, strat_escalations = await strategy.process(
                    state["extracted_telemetry"], 
                    thresholds, 
                    context,
                    llm_service=self._llm_service
                )
                state["extracted_telemetry"].update(processed_data)
                escalations.extend(strat_escalations)
            except KeyError:
                logger.error(f"Strategy {strategy_id} not found in registry.")

        # ---- NODE 3: HUMAN INTERCEPT ----
        state["current_node"] = "human_intercept"
        
        # Apply injected global safety rules (Fallback)
        for rule in self._safety_rules:
            is_anomaly, reason = rule.evaluate(state["extracted_telemetry"], conf_score, thresholds=thresholds)
            if is_anomaly:
                escalations.append(reason)
                
        if escalations:
            state["requires_review"] = True
            state["is_paused"] = True
            state["session_status"] = SessionStatus.AWAITING_EXPERT_INTERVENTION
            escalation_details = "; ".join(escalations)
            state["output_message"] = (
                f"I've identified findings that need immediate attention: {escalation_details}. "
                f"I'm connecting you directly with the expert."
            )
            await self._save_state(session_id, state)
            return state
            
        # ---- NODE 4: ACTION DISPATCH ----
        state["current_node"] = "action_dispatch"
        
        # Advance the step since this task completed without escalation
        state["current_step_index"] += 1
        
        # Final message formulation
        state["output_message"] = (
            "I've gathered the necessary information for this step. Let's proceed."
        )

        await self._save_state(session_id, state)
        return state

    async def _save_state(self, session_id: UUID, state: AgentState):
        chunk_ids = []
        await self._session_repo.create_execution_trace(
            session_id, state["current_node"], state["user_query"],
            state["output_message"], chunk_ids, state["classification_score"],
        )
        await self._session_repo.save_active_session(
            session_id, UUID(state["conversation_id"]), UUID(state["config_id"]),
            state["current_node"], state,
            state["is_paused"], state["requires_review"],
        )

    async def execute_synthesis_subgraph(self, session_id: UUID, is_partial: bool, reason: str):
        logger.info(f"LangGraph executing synthesis subgraph for session {session_id}")
        if not self._preconsult_repo or not self._embedding_service:
            return
        try:
            structured_data = {
                "is_partial": is_partial,
                "reason": reason
            }
            embedding = self._embedding_service.get_embedding(str(structured_data))
            await self._preconsult_repo.atomic_insert_summary_and_update_state(
                session_id=session_id,
                structured_data=structured_data,
                summary_embedding=embedding
            )
        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
