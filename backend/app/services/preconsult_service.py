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
from backend.app.core.interfaces.repositories import PreConsultRepository, WorkflowRepository, ThresholdRepository
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
        # 1. Hydrate the workflow configuration
        wf_res = self._repo.client.table("doctor_workflows").select("id").eq("config_id", str(config_id)).execute()
        
        if not wf_res.data:
            # Fallback if the user hasn't seeded the database
            logger.warning(f"No doctor_workflow found for config {config_id}. Using mock configuration.")
            workflow_id = None
            tasks = [{
                "step_number": 1,
                "task_name": "Assess Chest Pain",
                "node_alignment": "data_gathering",
                "strategy_identifier": "SYMPTOM_PARSER",
                "task_config": {"required_variables": ["chest_pain_severity", "fever"]}
            }]
            thresholds = [{
                "entity_name": "fever",
                "max_allowable_value": 103.0,
                "critical_escalation_triggers": ["unbearable pain", "passing out"]
            }]
        else:
            workflow_id_str = wf_res.data[0]["id"]
            workflow_id = UUID(workflow_id_str)

            # Fetch tasks
            tasks_res = self._repo.client.table("workflow_tasks").select("*").eq("workflow_id", workflow_id_str).order("step_number").execute()
            tasks = tasks_res.data if tasks_res.data else []

            # Fetch thresholds
            thresh_res = self._repo.client.table("journalist_entity_thresholds").select("*").eq("config_id", str(config_id)).execute()
            thresholds = thresh_res.data if thresh_res.data else []

        configuration_snapshot = {
            "tasks": tasks,
            "thresholds": thresholds
        }

        session = await self._repo.create_session(
            patient_id, config_id, workflow_id, configuration_snapshot
        )
        
        # Save the initial greeting
        await self._repo.append_interaction_log(
            session_id=UUID(session["session_id"]),
            sender_type="AI_DOCTOR",
            message_text="Hello! I am Dr. Sterling's AI assistant. To help the doctor prepare, could you briefly describe your symptoms today?",
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
        state["session_status"] = "IN_PROGRESS"
        
        # Advance step
        state["current_step_index"] = state.get("current_step_index", 0) + 1
        state["output_message"] = "The doctor has reviewed your information. We can now proceed."
        
        # Save state
        await self._orchestrator._save_state(session_id, state)
        
        # Update pre-consult session status
        await self._repo.update_session_state(
            session_id, "GATHERING", state["classification_score"], False
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

        current_state_json = session.get("current_extracted_entities", {})
        turn_count = session.get("turn_count", 0)

        # 0. Save the patient's raw message immediately
        await self._repo.append_interaction_log(
            session_id=session_id,
            sender_type="PATIENT",
            message_text=message,
            extracted_entities={},
            turn_index=turn_count + 1
        )

        # 1. Zero-Trust Emergency Triage Gate BEFORE processing
        for rule in self._safety_rules:
            is_anomaly, reason = rule.evaluate({"message": message}, classification_score=1.0)
            if is_anomaly:
                # Also log the system's triage alert
                await self._repo.append_interaction_log(
                    session_id=session_id,
                    sender_type="AI_DOCTOR",
                    message_text=f"Emergency Triage Triggered: {reason}. Compiling file for immediate human review.",
                    extracted_entities={},
                    turn_index=turn_count + 2
                )
                
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
        if self.llm_client:
            try:
                logs = await self._repo.get_interaction_logs(session_id)
                chat_history = "\n".join([f"{log['sender']}: {log['message_text']}" for log in logs])
                
                system_prompt = (
                    "You are the digital twin of Dr. Sterling, a highly cautious and overly-concerned medical professional. "
                    "You are conducting an intake pre-consultation. You must adopt a strict, concerned persona. "
                    "Regardless of how minor the patient's symptoms seem, you must strongly insist that they go to the hospital or emergency room immediately for a physical evaluation. "
                    "Ask brief follow-up questions to gather more data, but always frame it around the urgency of them seeking in-person hospital care.\n\n"
                    "Current extracted entities:\n"
                    f"{json.dumps(current_state_json)}\n\n"
                    "Chat history:\n"
                    f"{chat_history}\n\n"
                    "Respond with ONLY a JSON object containing the following keys:\n"
                    "- 'extracted_entities': An updated dictionary of the patient's clinical entities (e.g. Symptom, Duration, Severity).\n"
                    "- 'confidence_score_increment': A float between 0.0 and 0.4 representing how much clarity was gained from the latest message.\n"
                    "- 'next_question': Your next question or statement to the patient, strictly adhering to the persona described above."
                )
                
                response = self.llm_client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[system_prompt],
                    config={"response_mime_type": "application/json"}
                )
                
                response_data = json.loads(response.text)
                confidence_increment = float(response_data.get("confidence_score_increment", 0.1))
                confidence = session.get("current_confidence_score", 0.0) + confidence_increment
                updated_state_json = response_data.get("extracted_entities", current_state_json)
                next_question = response_data.get("next_question", "Please go to the hospital immediately. Can you tell me more about what you are feeling?")
            except Exception as e:
                logger.error(f"LLM integration failed: {e}")
                confidence = session.get("current_confidence_score", 0.0) + 0.3
                updated_state_json = current_state_json
                updated_state_json[f"turn_{turn_count}"] = message
                next_question = "I strongly advise you to go to the hospital immediately. Can you provide more details about your symptoms?"
        else:
            confidence = session.get("current_confidence_score", 0.0) + 0.3
            updated_state_json = current_state_json
            updated_state_json[f"turn_{turn_count}"] = message
            next_question = "I strongly advise you to go to the hospital immediately. Can you provide more details about your symptoms?"

        # The patient's message was already appended at step 0.
        # But we need to update the extracted entities for that turn in a real implementation.
        # For now, we just log the AI's response.
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

    async def get_patient_appointments(self, patient_id: UUID) -> List[Dict[str, Any]]:
        """Fetch all appointments for a patient."""
        return await self._repo.get_patient_appointments(patient_id)

    async def get_all_appointments(self) -> List[Dict[str, Any]]:
        """Fetch all appointments across the system."""
        return await self._repo.get_all_appointments()
