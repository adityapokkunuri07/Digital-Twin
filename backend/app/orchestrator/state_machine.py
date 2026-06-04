"""
Zero-Trust Orchestrator — LangGraph 4-Node State Machine.

Refactored to follow Open/Closed Principle:
- Data extraction is delegated to injected List[DataExtractor]
- Anomaly detection is delegated to injected List[SafetyRule]
- Adding new extractors or safety rules requires ZERO changes to this file

Depends on segregated repository interfaces (DIP):
- ConfigRepository for workflow config loading
- SessionRepository for state checkpointing and telemetry
"""
from typing import TypedDict, Dict, Any, List
from uuid import UUID, uuid4
import logging

from backend.app.core.interfaces.repositories import ConfigRepository, SessionRepository
from backend.app.services.hybrid_rag_service import HybridRAGEngine
from backend.app.orchestrator.extractors.base import DataExtractor
from backend.app.orchestrator.safety_rules.base import SafetyRule

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """Typed state schema for the LangGraph execution thread."""
    session_id: str
    conversation_id: str
    config_id: str
    current_node: str
    user_query: str
    gathered_data: Dict[str, Any]
    retrieved_context: str
    output_message: str
    requires_review: bool
    is_paused: bool
    classification_score: float
    history: List[Dict[str, Any]]


class ZeroTrustOrchestrator:
    """
    4-Node LangGraph execution engine with pluggable extractors and safety rules.

    Nodes:
        1. Data Gathering — Adaptive extraction loops via injected extractors
        2. Data Processing — Cross-reference against SSOT via Hybrid RAG
        3. Human Intercept — Circuit breaker triggered by injected safety rules
        4. Action Dispatch — Deterministic function execution

    Open/Closed: New extractors and safety rules are injected at construction time.
    To add a new extraction pattern or safety check, create a new class implementing
    DataExtractor or SafetyRule and register it in the ServiceProvider.
    """

    def __init__(
        self,
        config_repo: ConfigRepository,
        session_repo: SessionRepository,
        rag_engine: HybridRAGEngine,
        extractors: List[DataExtractor] | None = None,
        safety_rules: List[SafetyRule] | None = None,
    ):
        self._config_repo = config_repo
        self._session_repo = session_repo
        self._rag_engine = rag_engine
        self._extractors = extractors or []
        self._safety_rules = safety_rules or []

    async def initialize_session(
        self, conversation_id: UUID, config_id: UUID
    ) -> Dict[str, Any]:
        """Create a new execution session with a clean initial state."""
        session_id = uuid4()
        initial_state: AgentState = {
            "session_id": str(session_id),
            "conversation_id": str(conversation_id),
            "config_id": str(config_id),
            "current_node": "start",
            "user_query": "",
            "gathered_data": {},
            "retrieved_context": "",
            "output_message": "Hello. I am your Digital Twin. How can I assist you today?",
            "requires_review": False,
            "is_paused": False,
            "classification_score": 1.0,
            "history": [],
        }

        await self._session_repo.save_active_session(
            session_id, conversation_id, config_id,
            initial_state["current_node"], initial_state,
            initial_state["is_paused"], initial_state["requires_review"],
        )
        return initial_state

    async def run_step(
        self, session_id: UUID, user_query: str
    ) -> Dict[str, Any]:
        """
        Execute a single transition step in the 4-node state machine.

        Flow:
        1. Load session checkpoint
        2. Check concurrency lock (frozen sessions are rejected)
        3. Node 1: Run all DataExtractors against user input
        4. Check if all required inputs are gathered
        5. Node 2: Data Processing via Hybrid RAG
        6. Node 3: Run all SafetyRules — escalate if any trigger
        7. Node 4: Action Dispatch — formulate response
        8. Write telemetry trace
        9. Save updated checkpoint
        """
        # 1. Load session checkpoint
        session_record = await self._session_repo.get_active_session(session_id)
        if not session_record:
            raise ValueError(f"Session with ID '{session_id}' not found.")

        state: AgentState = session_record["graph_state"]
        state["user_query"] = user_query

        # 2. Concurrency lock check
        if state.get("is_paused", False) or state.get("requires_review", False):
            state["output_message"] = (
                "This session has been suspended and is awaiting expert human review. "
                "Operations are frozen."
            )
            return state

        config_id = UUID(state["config_id"])
        config_record = await self._config_repo.get_expert_config(config_id)
        workflow_config = config_record.get("workflow_config", {}) if config_record else {}
        steps = workflow_config.get("steps", [])

        # Collect all required inputs from workflow config
        all_required_inputs = list(set(
            inp
            for step in steps
            for inp in step.get("inputs", [])
        ))

        # 3. Node 1: Data Gathering — run all injected extractors
        text = user_query.lower()
        for extractor in self._extractors:
            extracted = extractor.extract(text)
            state["gathered_data"].update(extracted)

        # Check if we're still missing required variables
        missing_inputs = [
            x for x in all_required_inputs
            if x not in state["gathered_data"]
        ]

        selected_chunks = []

        if missing_inputs:
            # Stay in data gathering loop
            state["current_node"] = "data_gathering"
            state["output_message"] = (
                f"Please provide the following clinical metrics to proceed: "
                f"{', '.join(missing_inputs)}."
            )
        else:
            # 4. Node 2: Data Processing — Hybrid RAG context retrieval
            context, selected_chunks, rejected = await self._rag_engine.retrieve_context(
                config_id, user_query,
            )
            state["retrieved_context"] = context
            state["current_node"] = "processing"

            # Get classification score from top chunk
            top_score = (
                selected_chunks[0]["combined_score"] if selected_chunks else 0.0
            )
            state["classification_score"] = top_score

            # 5. Node 3: Run all injected safety rules
            anomaly_reasons = []
            for rule in self._safety_rules:
                is_anomaly, reason = rule.evaluate(
                    state["gathered_data"], top_score,
                )
                if is_anomaly:
                    anomaly_reasons.append(reason)

            if anomaly_reasons:
                # Human Intercept — freeze thread
                state["current_node"] = "human_intercept"
                state["requires_review"] = True
                state["is_paused"] = True
                state["output_message"] = (
                    f"CRITICAL ESCALATION TRIGGERED: {'; '.join(anomaly_reasons)}. "
                    "Auto-pilot halted. Your session has been frozen and routed "
                    "to an expert physician for intercept."
                )
            else:
                # 6. Node 4: Action Dispatch
                state["current_node"] = "action_dispatch"
                summary = "Clinical parameters verified against guidelines.\n"
                if selected_chunks:
                    summary += f"Guideline Recommendation: {selected_chunks[0]['content']}"
                state["output_message"] = summary

        # 7. Write telemetry trace
        chunk_ids = [UUID(c["chunk_id"]) for c in selected_chunks]
        await self._session_repo.create_execution_trace(
            session_id, state["current_node"], user_query,
            state["output_message"], chunk_ids, state["classification_score"],
        )

        # 8. Save updated session checkpoint
        await self._session_repo.save_active_session(
            session_id, UUID(state["conversation_id"]), config_id,
            state["current_node"], state,
            state["is_paused"], state["requires_review"],
        )

        return state
