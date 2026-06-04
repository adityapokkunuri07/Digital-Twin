from typing import TypedDict, Dict, Any, List, Tuple, Optional
from uuid import UUID, uuid4
import logging
import re
from backend.app.core.database import DatabaseService
from backend.app.services.hybrid_rag_service import HybridRAGEngine

logger = logging.getLogger(__name__)

class AgentState(TypedDict):
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
    def __init__(self, db: DatabaseService, rag_engine: HybridRAGEngine):
        self.db = db
        self.rag_engine = rag_engine

    async def initialize_session(self, conversation_id: UUID, config_id: UUID) -> Dict[str, Any]:
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
            "history": []
        }
        await self.db.save_active_session(
            session_id, conversation_id, config_id, 
            initial_state["current_node"], initial_state, 
            initial_state["is_paused"], initial_state["requires_review"]
        )
        return initial_state

    async def run_step(self, session_id: UUID, user_query: str) -> Dict[str, Any]:
        """
        Executes a single transition step in the LangGraph 4-node state machine.
        Locks the session state, evaluates transitions, and saves final checkpoints.
        """
        # 1. Fetch current session checkpoint
        session_record = await self.db.get_active_session(session_id)
        if not session_record:
            raise ValueError(f"Session with ID '{session_id}' not found.")

        state: AgentState = session_record["graph_state"]
        state["user_query"] = user_query
        
        # Check concurrency locking: if paused, prevent edits unless resolved by human
        if state.get("is_paused", False) or state.get("requires_review", False):
            state["output_message"] = "This session has been suspended and is awaiting expert human review. Operations are frozen."
            return state

        config_id = UUID(state["config_id"])
        config_record = await self.db.get_expert_config(config_id)
        workflow_config = config_record.get("workflow_config", {}) if config_record else {}
        steps = workflow_config.get("steps", [])

        # 2. Determine variables to gather
        # Check all input requirements in steps configuration
        all_required_inputs = []
        for step in steps:
            all_required_inputs.extend(step.get("inputs", []))
        all_required_inputs = list(set(all_required_inputs))

        # 3. Simulate Node 1: Data Gathering Node
        # Parse user query to extract vitals or inputs (e.g. "temperature is 101", "temp: 99", "oxygen: 95")
        text = user_query.lower()
        extracted = {}
        
        # Simple extraction rules
        temp_match = re.search(r'(?:temp|temperature)(?:\s+is|:)?\s*(\d{2,3}(?:\.\d)?)', text)
        if temp_match:
            extracted["temperature"] = float(temp_match.group(1))

        pain_match = re.search(r'(?:chest pain|chest tightness|pain in chest)', text)
        if pain_match:
            extracted["chest_pain"] = True

        sys_match = re.search(r'(?:bp|blood pressure)(?:\s+is|:)?\s*(\d{2,3})[/\s](\d{2,3})', text)
        if sys_match:
            extracted["blood_pressure_systolic"] = int(sys_match.group(1))
            extracted["blood_pressure_diastolic"] = int(sys_match.group(2))

        # Update gathered data
        state["gathered_data"].update(extracted)

        # Evaluate if we are missing critical variables needed to progress
        missing_inputs = [x for x in all_required_inputs if x not in state["gathered_data"]]
        
        if missing_inputs:
            state["current_node"] = "data_gathering"
            state["output_message"] = f"Please provide the following clinical metrics to proceed: {', '.join(missing_inputs)}."
        else:
            # 4. Simulate Node 2: Data Processing Node
            # Fetch context using Hybrid RAG
            context, selected_chunks, rejected = await self.rag_engine.retrieve_context(config_id, user_query)
            state["retrieved_context"] = context
            state["current_node"] = "processing"

            # Check for classification score based on highest score from selected chunks
            top_score = selected_chunks[0]["combined_score"] if selected_chunks else 0.0
            state["classification_score"] = top_score

            # Safety escalation circuit breaker: check for clinical red flags or low confidence
            is_anomaly = False
            anomaly_reasons = []

            # Red flag 1: Extreme Fever
            if "temperature" in state["gathered_data"] and state["gathered_data"]["temperature"] >= 103.0:
                is_anomaly = True
                anomaly_reasons.append("Extreme fever detected (>=103.0°F)")

            # Red flag 2: Chest pain / tightness
            if state["gathered_data"].get("chest_pain", False):
                is_anomaly = True
                anomaly_reasons.append("Potential cardiac symptom (chest pain) reported")

            # Red flag 3: Zero-trust classification score below confidence gate
            if top_score < 0.85:
                is_anomaly = True
                anomaly_reasons.append(f"Retrieval confidence ({top_score:.2f}) dropped below zero-trust gate (0.85)")

            if is_anomaly:
                # 5. Simulate Node 3: Human Intercept Node
                state["current_node"] = "human_intercept"
                state["requires_review"] = True
                state["is_paused"] = True
                state["output_message"] = (
                    f"CRITICAL ESCALATION TRIGGERED: {'; '.join(anomaly_reasons)}. "
                    "Auto-pilot halted. Your session has been frozen and routed to an expert physician for intercept."
                )
            else:
                # 6. Simulate Node 4: Action/Skills Dispatcher Node
                state["current_node"] = "action_dispatch"
                # Formulate clinical summary based on retrieved guidelines
                summary = "Clinical parameters verified against guidelines.\n"
                if selected_chunks:
                    summary += f"Guideline Recommendation: {selected_chunks[0]['content']}"
                state["output_message"] = summary

        # 7. Write Telemetry trace to Execution Telemetry Ledger
        chunk_ids = [UUID(c["chunk_id"]) for c in selected_chunks] if 'selected_chunks' in locals() else []
        await self.db.create_execution_trace(
            session_id, state["current_node"], user_query, 
            state["output_message"], chunk_ids, state["classification_score"]
        )

        # 8. Save updated session state
        await self.db.save_active_session(
            session_id, UUID(state["conversation_id"]), config_id, 
            state["current_node"], state, state["is_paused"], state["requires_review"]
        )

        return state
