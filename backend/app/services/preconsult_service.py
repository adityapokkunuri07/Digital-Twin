"""
Pre-Consultation Workflow Service — State Controller
"""
import logging
from typing import Dict, Any, List
from uuid import UUID
from fastapi import BackgroundTasks
from datetime import datetime

from backend.app.core.interfaces.repositories import PreConsultRepository
from backend.app.orchestrator.safety_rules.base import SafetyRule

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

    async def start_session(self, patient_id: UUID, config_id: UUID) -> Dict[str, Any]:
        """Task 1 Init: Create a new session."""
        session = await self._repo.create_session(patient_id, config_id)
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
            
        return {
            "session": session,
            "summary": summary
        }

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

        current_state_json = session.get("current_extracted_entities", {})
        turn_count = session.get("turn_count", 0)

        # 1. Zero-Trust Emergency Triage Gate BEFORE processing
        for rule in self._safety_rules:
            is_anomaly, reason = rule.evaluate({"message": message}, classification_score=1.0)
            if is_anomaly:
                # Force partial synthesis trap and delegate to LangGraph background task
                await self._repo.update_session_state(session_id, "SYNTHESIZING_PARTIAL", 1.0)
                background_tasks.add_task(self._async_trigger_synthesis_graph, session_id, True, f"Emergency Triage: {reason}")
                return {"alert": f"Emergency Triage Triggered: {reason}. Compiling file for immediate human review."}

        # 2. Circuit Breaker for Knowledge Saturation Loop
        if turn_count >= self.MAX_TURNS_CIRCUIT_BREAKER:
            # Force partial synthesis trap and delegate to LangGraph background task
            await self._repo.update_session_state(session_id, "SYNTHESIZING_PARTIAL", session.get("current_confidence_score", 0.0))
            background_tasks.add_task(self._async_trigger_synthesis_graph, session_id, True, "Max turns reached")
            return {"alert": "Maximum turns reached. Compiling file for human review."}

        # 3. LLM-Driven Extraction and Confidence Scoring
        # Here we would normally call the LLM, passing ONLY `current_state_json` and `message`
        # For implementation purposes, we mock the LLM response.
        # In reality, this delegates to your Gemini pipeline.
        confidence = session.get("current_confidence_score", 0.0) + 0.3 # Mock increment
        updated_state_json = current_state_json
        updated_state_json[f"turn_{turn_count}"] = message # Mock extraction
        next_question = "Can you tell me more?" # Mock LLM response

        # 4. Increment turn count and update logs + running state
        await self._repo.append_interaction_log(
            session_id=session_id,
            sender_type="PATIENT",
            message_text=message,
            extracted_entities=updated_state_json,
            turn_index=turn_count + 1
        )
        
        await self._repo.append_interaction_log(
            session_id=session_id,
            sender_type="AI_DOCTOR",
            message_text=next_question,
            extracted_entities={},
            turn_index=turn_count + 2
        )

        await self._repo.update_session_state(
            session_id, "GATHERING", confidence, increment_turn=True, current_entities=updated_state_json
        )

        # 5. HTTP Timeout Bottleneck Mitigation: Delegate Synthesis to Background Task
        if confidence >= self.CONFIDENCE_THRESHOLD:
            await self._repo.update_session_state(session_id, "SYNTHESIZING", confidence)
            background_tasks.add_task(self._async_trigger_synthesis_graph, session_id, False, "")
            return {"response": "I have all the information I need. I am compiling your file for the doctor now."}

        return {"response": next_question}

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

    async def book_appointment(self, session_id: UUID, patient_id: UUID, doctor_id: UUID, scheduled_time: datetime) -> Dict[str, Any]:
        """Task 4: AI Coordinator completes the booking."""
        session = await self._repo.get_session(session_id)
        if not session or session.get("status") != "ALIGNING":
            raise ValueError("Session is not in ALIGNING state.")

        appointment = await self._repo.create_appointment(patient_id, session_id, doctor_id, scheduled_time)
        await self._repo.update_session_state(session_id, "BOOKED", session.get("current_confidence_score", 1.0))
        
        return appointment
