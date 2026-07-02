"""
Pre-Consultation Workflow Service — State Controller
"""
import logging
import json
from typing import Dict, Any, List
from uuid import UUID
from fastapi import BackgroundTasks
from datetime import datetime
from google import genai

from backend.app.core.config import settings
from backend.app.core.enums import SessionStatus
from backend.app.core.interfaces.repositories import PreConsultRepository, WorkflowRepository, ThresholdRepository
from backend.app.orchestrator.safety_rules.base import SafetyRule
from backend.app.services.context_synthesizer import ContextSynthesizer

logger = logging.getLogger(__name__)


class PreConsultationService:
    """
    Orchestrates the 4-task pre-consultation flow.
    Delegates Task 2 (Synthesis) to the LangGraph orchestrator via BackgroundTasks
    to prevent HTTP connection timeouts and ensure fault tolerance.
    """
    
    CONFIDENCE_THRESHOLD = 0.85
    MAX_TURNS_CIRCUIT_BREAKER = 10

    def __init__(
        self, 
        preconsult_repo: PreConsultRepository, 
        safety_rules: List[SafetyRule], 
        langgraph_orchestrator: Any, # Injected ZeroTrustOrchestrator
        workflow_repo: WorkflowRepository = None,
        threshold_repo: ThresholdRepository = None
    ):
        self._repo = preconsult_repo
        self._workflow_repo = workflow_repo
        self._threshold_repo = threshold_repo
        self._safety_rules = safety_rules or []
        self._orchestrator = langgraph_orchestrator
        
        # Initialize Gemini Client
        if settings.GEMINI_API_KEY:
            self.llm_client = genai.Client(api_key=settings.GEMINI_API_KEY)
        else:
            self.llm_client = None
            logger.warning("GEMINI_API_KEY is not set. PreConsultationService LLM integration will fail.")

    async def start_session(self, patient_id: UUID, config_id: UUID) -> Dict[str, Any]:
        """Task 1 Init: Create a new session with hydrated configuration snapshot."""
        
        # Check for existing session
        latest_session = await self._repo.get_latest_session(patient_id, config_id)
        injected_context = ""
        
        if latest_session:
            import datetime
            
            updated_at_str = latest_session.get("updated_at")
            if updated_at_str:
                # Handle supabase ISO format potentially ending in Z
                if updated_at_str.endswith('Z'):
                    updated_at_str = updated_at_str[:-1] + '+00:00'
                updated_at = datetime.datetime.fromisoformat(updated_at_str)
                if updated_at.tzinfo is None:
                    updated_at = updated_at.replace(tzinfo=datetime.timezone.utc)
                now = datetime.datetime.now(datetime.timezone.utc)
                age = now - updated_at
                
                if latest_session.get("status") not in ["BOOKED", "complete_booked"]:
                    if age.total_seconds() < 24 * 3600:
                        logger.info(f"Resuming recent session {latest_session['session_id']}")
                        # Fetch the active state to ensure it's still available in orchestrator
                        active_state = await self._orchestrator._session_repo.get_active_session(UUID(str(latest_session["session_id"])))
                        if active_state:
                            return latest_session
            
            # If we didn't resume, prepare injected context from previous session
            prev_entities = latest_session.get("current_extracted_entities", {})
            if prev_entities:
                import json
                injected_context = (
                    f"System Note: The account owner had a previous session with these symptoms: "
                    f"{json.dumps(prev_entities)}. Goal 1: Determine if the current user is continuing that issue "
                    f"OR starting a new issue. Goal 2: Determine if this consultation is for themselves or someone else "
                    f"(extract as `target_patient_relation`). If it is for someone else, completely ignore the previous symptoms."
                )

        # 1. Hydrate the workflow configuration
        # Temporarily use doctor_workflows until DB migration is run
        wf_res = self._repo.client.table("doctor_workflows").select("id").eq("config_id", str(config_id)).execute()
        
        if not wf_res.data:
            # Fallback if the user hasn't seeded the database
            logger.warning(f"No doctor_workflow found for config {config_id}. Using mock configuration.")
            workflow_id = None
            tasks = [{
                "step_number": 1,
                "task_name": "Initial Assessment",
                "node_alignment": "data_gathering",
                "strategy_identifier": "GENERAL_INTAKE",
                "task_config": {"required_variables": ["primary_concern", "urgency_level", "target_patient_relation"]}
            }]
            thresholds = [{
                "entity_name": "urgency_level",
                "max_allowable_value": 5.0,
                "critical_escalation_triggers": ["immediate risk", "system failure"]
            }]
        else:
            workflow_id_str = wf_res.data[0]["id"]
            workflow_id = UUID(workflow_id_str)

            # Fetch tasks
            tasks_res = self._repo.client.table("workflow_tasks").select("*").eq("workflow_id", workflow_id_str).order("step_number").execute()
            tasks = tasks_res.data if tasks_res.data else []

            # Fetch thresholds (temporarily use journalist_entity_thresholds until DB migration is run)
            thresh_res = self._repo.client.table("journalist_entity_thresholds").select("*").eq("config_id", str(config_id)).execute()
            thresholds = thresh_res.data if thresh_res.data else []

        configuration_snapshot = {
            "tasks": tasks,
            "thresholds": thresholds
        }

        session = await self._repo.create_session(
            patient_id, config_id, workflow_id, configuration_snapshot
        )
        
        # Override initial node to probing
        session["current_node"] = "probing"
        # We must explicitly create the active_sessions table row so the orchestrator can read it.
        import uuid
        initial_state = {
            "session_id": str(session["session_id"]),
            "conversation_id": str(uuid.uuid4()),
            "config_id": str(config_id),
            "workflow_id": str(workflow_id) if workflow_id else "",
            "current_step_index": 0,
            "assigned_actor": "TWIN",
            "session_status": "GATHERING",
            "current_node": "probing",
            "user_query": "",
            "extracted_telemetry": {},
            "configuration_snapshot": configuration_snapshot,
            "retrieved_context": injected_context,
            "output_message": "",
            "requires_review": False,
            "is_paused": False,
            "classification_score": 0.0,
            "history": [],
            "expert_override_message": "",
            "end_user_consent_granted": False,
            "pending_action": ""
        }
        await self._orchestrator._save_state(UUID(session["session_id"]), initial_state)
        
        # Save the initial greeting
        await self._repo.append_interaction_log(
            session_id=UUID(session["session_id"]),
            sender_type="AI_DOCTOR",
            message_text="Hello! I am the AI assistant. How can I help you today?",
            extracted_entities={},
            turn_index=0
        )
        
        return session

    async def align_and_release(self, session_id: UUID) -> Dict[str, Any]:
        """
        Unfreeze the session after doctor review and advance the workflow step.
        """
        session_record = await self._orchestrator._session_repo.get_active_session(session_id)
        if not session_record:
            raise ValueError(f"Session '{session_id}' not found.")

        state = session_record["graph_state"]
        
        # Unfreeze
        state["is_paused"] = False
        state["requires_review"] = False
        state["session_status"] = SessionStatus.AWAITING_USER_INPUT
        
        # Advance step
        state["current_step_index"] = state.get("current_step_index", 0) + 1
        state["output_message"] = "The doctor has reviewed your information. We can now proceed."
        
        # Save state
        await self._orchestrator._save_state(session_id, state)
        
        # Update pre-consult session status
        await self._repo.update_session_state(
            session_id, SessionStatus.AWAITING_USER_INPUT, state["classification_score"], False
        )
        
        return state

    async def get_escalation_context(self, session_id: UUID) -> Dict[str, Any]:
        """
        Provide side-by-side comparison of patient data vs thresholds for the doctor.
        """
        session_record = await self._orchestrator._session_repo.get_active_session(session_id)
        if not session_record:
            raise ValueError(f"Session '{session_id}' not found.")

        state = session_record["graph_state"]
        snapshot = state.get("configuration_snapshot", {})
        
        return {
            "patient_data": state.get("extracted_telemetry", {}),
            "thresholds": snapshot.get("thresholds", []),
            "current_step": state.get("current_step_index", 0),
            "tasks": snapshot.get("tasks", [])
        }

    async def get_session_details(self, session_id: UUID) -> Dict[str, Any]:
        """Fetch the current session state and synthesis summary."""
        session = await self._repo.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found.")
            
        summary = None
        if session.get("status") in [SessionStatus.AWAITING_EXPERT_INTERVENTION, SessionStatus.AWAITING_BOOKING, SessionStatus.COMPLETE_BOOKED]:
            # In a real app, query `pre_consult_summaries` table.
            # Mocking here for simulation based on current entities.
            summary = {
                "structured_clinical_data": session.get("current_extracted_entities", {}),
                "doctor_review_notes": session.get("doctor_review_notes", None)
            }
            
        logs = await self._repo.get_interaction_logs(session_id)
        
        return {
            "session": session,
            "summary": summary,
            "logs": logs
        }

    async def get_pending_queue(self) -> List[Dict[str, Any]]:
        """Fetch all sessions that are waiting for doctor review."""
        try:
            response = self._repo.client.table('pre_consultation_sessions') \
                .select('session_id, status, current_confidence_score, updated_at, patients!fk_patient(full_name, email)') \
                .in_('status', ['PENDING_REVIEW', SessionStatus.AWAITING_EXPERT_INTERVENTION.value]) \
                .order('updated_at', desc=True) \
                .execute()
            
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Error fetching pending queue: {e}")
            return []

    async def _async_trigger_synthesis_graph(self, session_id: UUID, is_partial: bool, reason: str):
        """
        Background Task: Executes the Synthesis node of the LangGraph state machine asynchronously.
        """
        try:
            # We call a newly added method on the existing LangGraph orchestrator
            await self._orchestrator.execute_synthesis_subgraph(session_id, is_partial, reason)
        except Exception as e:
            logger.error(f"LangGraph Background Synthesis Failed for session {session_id}: {e}")

    async def process_chat_turn(self, session_id: UUID, message: str, background_tasks: BackgroundTasks) -> Dict[str, Any]:
        """
        Task 1 Loop: Gather data, evaluate safety, and calculate confidence.
        Delegates execution logic to the ZeroTrustOrchestrator.
        """
        session = await self._repo.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found.")

        turn_count = session.get("turn_count", 0)

        # 0. Save the patient's raw message immediately
        await self._repo.append_interaction_log(
            session_id=session_id,
            sender_type="PATIENT",
            message_text=message,
            extracted_entities={},
            turn_index=turn_count + 1
        )

        # 1. Circuit Breaker for Knowledge Saturation Loop
        if turn_count >= self.MAX_TURNS_CIRCUIT_BREAKER:
            await self._repo.update_session_state(session_id, SessionStatus.PROCESSING_PARTIAL_SYNTHESIS, session.get("current_confidence_score", 0.0))
            background_tasks.add_task(self._async_trigger_synthesis_graph, session_id, True, "Max turns reached")
            return {"alert": "Maximum turns reached. Compiling file for human review."}

        # 2. Delegate to Zero-Trust Orchestrator
        try:
            state = await self._orchestrator.run_step(session_id, message)
        except Exception as e:
            import traceback
            err_msg = traceback.format_exc()
            logger.error(f"Orchestrator execution failed: {err_msg}")
            return {"alert": f"System error occurred during processing: {str(e)}\n\n{err_msg}"}

        output_message = state.get("output_message", "Processing...")
        extracted_telemetry = state.get("extracted_telemetry", {})
        classification_score = state.get("classification_score", 0.0)

        # 3. Save the interaction log and update state appropriately
        await self._repo.append_interaction_log(
            session_id=session_id,
            sender_type="AI_DOCTOR",
            message_text=output_message,
            extracted_entities=extracted_telemetry,
            turn_index=turn_count + 2
        )

        if state.get("session_status") == SessionStatus.AWAITING_EXPERT_INTERVENTION:
            await self._repo.update_session_state(
                session_id, SessionStatus.AWAITING_EXPERT_INTERVENTION, classification_score, increment_turn=True, current_entities=extracted_telemetry
            )
            return {"response": output_message, "alert": output_message}

        elif state.get("current_node") == "action_dispatch":
            await self._repo.update_session_state(
                session_id, SessionStatus.PROCESSING_SYNTHESIS, classification_score, increment_turn=True, current_entities=extracted_telemetry
            )
            background_tasks.add_task(self._async_trigger_synthesis_graph, session_id, False, "")
            return {"response": output_message}
            
        else:
            await self._repo.update_session_state(
                session_id, SessionStatus.AWAITING_USER_INPUT, classification_score, increment_turn=True, current_entities=extracted_telemetry
            )
            return {"response": output_message}

    async def submit_doctor_review(self, session_id: UUID, doctor_notes: str) -> Dict[str, Any]:
        """Task 3: Doctor reviews the synthesized data."""
        session = await self._repo.get_session(session_id)
        if not session or session.get("status") != SessionStatus.AWAITING_EXPERT_INTERVENTION:
            raise ValueError("Session is not ready for review.")
            
        # In a real scenario, we might also update the pre_consult_summaries row here 
        # to save the doctor_notes, requiring another repo method.
        # For now, we update the state.
        res = await self._repo.update_session_state(session_id, SessionStatus.AWAITING_BOOKING, session.get("current_confidence_score", 1.0))
        return res

    async def inject_doctor_message(self, session_id: UUID, message: str) -> Dict[str, Any]:
        """Inject a direct message from the doctor to the patient."""
        session = await self._repo.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found.")

        turn_count = session.get("turn_count", 0)

        await self._repo.append_interaction_log(
            session_id=session_id,
            sender_type="AI_DOCTOR",
            message_text=f"DIRECT MESSAGE FROM DOCTOR: {message}",
            extracted_entities={},
            turn_index=turn_count + 1
        )
        
        await self._repo.update_session_state(
            session_id, SessionStatus.AWAITING_USER_INPUT, session.get("current_confidence_score", 0.0), increment_turn=True
        )
        return {"status": "success"}

    async def book_appointment(self, session_id: UUID, patient_id: UUID, expert_id: UUID, scheduled_time: datetime) -> Dict[str, Any]:
        """Task 4: AI Coordinator completes the booking via Federation Layer."""
        from backend.app.services.booking_adapter import BookingAdapter
        
        session = await self._repo.get_session(session_id)
        if not session or session.get("status") != SessionStatus.AWAITING_BOOKING:
            raise ValueError("Session is not in ALIGNING state.")

        appointment = await BookingAdapter().book_appointment(str(expert_id), scheduled_time, {"patient_id": str(patient_id)})
        await self._repo.update_session_state(session_id, SessionStatus.COMPLETE_BOOKED, session.get("current_confidence_score", 1.0))
        
        return appointment

    async def get_active_sessions(self) -> List[Dict[str, Any]]:
        """Fetch all sessions currently being processed (GATHERING, SYNTHESIZING, etc.)."""
        return await self._repo.get_active_sessions()
