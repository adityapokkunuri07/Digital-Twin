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
from backend.app.core.interfaces.repositories import PreConsultRepository
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
        langgraph_orchestrator: Any # Injected ZeroTrustOrchestrator
    ):
        self._repo = preconsult_repo
        self._safety_rules = safety_rules or []
        self._orchestrator = langgraph_orchestrator
        
        # Initialize Gemini Client
        if settings.GEMINI_API_KEY:
            self.llm_client = genai.Client(api_key=settings.GEMINI_API_KEY)
        else:
            self.llm_client = None
            logger.warning("GEMINI_API_KEY is not set. PreConsultationService LLM integration will fail.")

    async def start_session(self, patient_id: UUID, config_id: UUID) -> Dict[str, Any]:
        """Task 1 Init: Create a new session."""
        session = await self._repo.create_session(patient_id, config_id)
        session_id = UUID(session["session_id"])
        
        # Initialize LangGraph state machine with the same session ID
        state = await self._orchestrator.initialize_session(
            conversation_id=session_id, 
            config_id=config_id,
            session_id=session_id
        )
        greeting = state["output_message"]
        
        # Save the initial greeting
        await self._repo.append_interaction_log(
            session_id=session_id,
            sender_type="AI_DOCTOR",
            message_text=greeting,
            extracted_entities={},
            turn_index=0
        )
        
        return session

    async def get_session_details(self, session_id: UUID) -> Dict[str, Any]:
        """Fetch the current session state and synthesis summary."""
        session = await self._repo.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found.")
            
        summary = None
        if session.get("status") in ["PENDING_REVIEW", "ALIGNING", "BOOKED"]:
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
                .eq('status', 'PENDING_REVIEW') \
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
        If threshold reached, offload to Task 2 (Synthesis) via background task.
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

        # 0.5 Greeting Bypass
        lower_msg = message.strip().lower()
        if len(lower_msg.split()) < 6 and any(greet in lower_msg for greet in ["hi", "hello", "hey", "hii", "heyy"]):
            output_msg = "Hello! I am Dr. Sterling's AI assistant. To help the doctor prepare, could you briefly describe your symptoms today?"
            await self._repo.append_interaction_log(
                session_id=session_id,
                sender_type="AI_DOCTOR",
                message_text=output_msg,
                extracted_entities={},
                turn_index=turn_count + 2
            )
            await self._repo.update_session_state(session_id, "GATHERING", 1.0, increment_turn=True)
            return {"response": output_msg}

        # Zero-Trust execution via LangGraph Orchestrator
        try:
            # Fallback initialization for older sessions
            session_record = await self._orchestrator._session_repo.get_active_session(session_id)
            if not session_record:
                await self._orchestrator.initialize_session(
                    conversation_id=session_id, 
                    config_id=UUID(session["config_id"]),
                    session_id=session_id
                )

            state = await self._orchestrator.run_step(session_id, message)
            
            output_msg = state.get("output_message", "I am processing your information.")
            is_paused = state.get("is_paused", False)
            current_node = state.get("current_node", "")
            
            await self._repo.append_interaction_log(
                session_id=session_id,
                sender_type="AI_DOCTOR",
                message_text=output_msg,
                extracted_entities=state.get("gathered_data", {}),
                turn_index=turn_count + 2
            )
            
            # Map graph state to PreConsultation UI state
            if is_paused:
                # Triggers doctor review UI
                await self._repo.update_session_state(
                    session_id, "PENDING_REVIEW", state.get("classification_score", 1.0),
                    increment_turn=True, current_entities=state.get("gathered_data", {})
                )
                return {"response": output_msg, "alert": "Session suspended for human review."}
                
            elif current_node == "action_dispatch":
                # Dispatched
                await self._repo.update_session_state(
                    session_id, "SYNTHESIZING", 1.0, 
                    increment_turn=True, current_entities=state.get("gathered_data", {})
                )
                background_tasks.add_task(self._async_trigger_synthesis_graph, session_id, False, "Completed Workflow")
                return {"response": output_msg}
                
            else:
                await self._repo.update_session_state(
                    session_id, "GATHERING", state.get("classification_score", 0.5), 
                    increment_turn=True, current_entities=state.get("gathered_data", {})
                )
                return {"response": output_msg}
        except Exception as e:
            logger.error(f"Orchestrator error: {e}", exc_info=True)
            fallback_msg = f"ERROR: {type(e).__name__} - {str(e)}"
            await self._repo.append_interaction_log(
                session_id=session_id,
                sender_type="AI_DOCTOR",
                message_text=fallback_msg,
                extracted_entities={},
                turn_index=turn_count + 2
            )
            await self._repo.update_session_state(session_id, "GATHERING", 0.0, increment_turn=True)
            return {"response": fallback_msg}

    async def submit_doctor_review(self, session_id: UUID, doctor_notes: str) -> Dict[str, Any]:
        """Task 3: Doctor reviews the synthesized data."""
        session = await self._repo.get_session(session_id)
        if not session or session.get("status") != "PENDING_REVIEW":
            raise ValueError("Session is not ready for review.")
            
        # In a real scenario, we might also update the pre_consult_summaries row here 
        # to save the doctor_notes, requiring another repo method.
        # For now, we update the state.
        res = await self._repo.update_session_state(session_id, "ALIGNING", session.get("current_confidence_score", 1.0))
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
        
        # Inject into LangGraph state history so LLM has context
        session_record = await self._orchestrator._session_repo.get_active_session(session_id)
        if session_record:
            state = session_record["graph_state"]
            state["history"].append({"role": "doctor", "content": f"DIRECT MESSAGE FROM DOCTOR: {message}"})
            # Unpause the session so the patient can respond
            state["is_paused"] = False
            state["requires_review"] = False
            state["current_node"] = "action_dispatch" # Or keep GATHERING
            await self._orchestrator._session_repo.save_active_session(
                session_id, UUID(state["conversation_id"]), UUID(state["config_id"]),
                state["current_node"], state,
                state["is_paused"], state["requires_review"]
            )
            
        await self._repo.update_session_state(
            session_id, "GATHERING", session.get("current_confidence_score", 0.0), increment_turn=True
        )
        return {"status": "success"}

    async def book_appointment(self, session_id: UUID, patient_id: UUID, doctor_id: UUID, scheduled_time: datetime) -> Dict[str, Any]:
        """Task 4: AI Coordinator completes the booking."""
        session = await self._repo.get_session(session_id)
        if not session or session.get("status") != "ALIGNING":
            raise ValueError("Session is not in ALIGNING state.")

        appointment = await self._repo.create_appointment(patient_id, session_id, doctor_id, scheduled_time)
        await self._repo.update_session_state(session_id, "BOOKED", session.get("current_confidence_score", 1.0))
        
        return appointment

    async def get_patient_appointments(self, patient_id: UUID) -> List[Dict[str, Any]]:
        """Fetch all appointments for a patient."""
        return await self._repo.get_patient_appointments(patient_id)

    async def get_all_appointments(self) -> List[Dict[str, Any]]:
        """Fetch all appointments across the system."""
        return await self._repo.get_all_appointments()
