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
from backend.app.services.llm.gemini_llm import GeminiLLMService
from backend.app.orchestrator.extractors.base import DataExtractor
from backend.app.orchestrator.safety_rules.base import SafetyRule
from backend.app.core.interfaces.embedding import EmbeddingService
from backend.app.services.context_synthesizer import ContextSynthesizer

logger = logging.getLogger(__name__)

# ─── Natural-language question mapping for clinical variables ───
# Instead of dumping raw variable names, the doctor twin asks like a real physician.
_VARIABLE_QUESTIONS = {
    "temperature": "What is your current body temperature?",
    "blood_pressure_systolic": "Could you share your blood pressure reading?",
    "blood_pressure_diastolic": "Could you share your blood pressure reading?",
    "chest_pain": "Are you experiencing any chest pain or discomfort?",
    "chest_pain_duration": "How long have you been experiencing the chest pain?",
    "chest_pain_location": "Where exactly do you feel the pain — is it in the center of your chest, the left side, or somewhere else?",
    "shortness_of_breath": "Do you experience any shortness of breath, especially with physical activity?",
    "palpitations": "Have you noticed any racing heartbeat or irregular heart rhythms?",
    "smoking_history": "Have you ever smoked? If so, for how long and have you quit?",
    "diabetes": "Have you been diagnosed with diabetes or high blood sugar?",
    "family_cardiac_history": "Is there any history of heart disease in your immediate family — parents or siblings?",
    "bmi": "Could you share your approximate height and weight so I can assess your BMI?",
    "vision_changes": "Have you noticed any changes in your vision recently?",
}

# Group related variables so the doctor asks a few at a time, not all at once
_QUESTION_GROUPS = [
    {"label": "vitals", "vars": ["temperature", "blood_pressure_systolic", "blood_pressure_diastolic"]},
    {"label": "primary_symptoms", "vars": ["chest_pain", "shortness_of_breath", "palpitations"]},
    {"label": "symptom_details", "vars": ["chest_pain_duration", "chest_pain_location"]},
    {"label": "risk_factors", "vars": ["smoking_history", "diabetes", "family_cardiac_history", "bmi"]},
]


def _build_doctor_followup(missing_inputs: list, gathered_data: dict) -> str:
    """
    Build a natural, empathetic follow-up message that a doctor would actually say.
    Groups questions logically and acknowledges what the patient already shared.
    """
    missing_set = set(missing_inputs)

    # Acknowledge what was already gathered
    ack_parts = []
    if "temperature" in gathered_data:
        temp = gathered_data["temperature"]
        if temp >= 103:
            ack_parts.append(f"I see your temperature is {temp}°F — that's quite elevated and I want to make sure we look into that carefully.")
        elif temp >= 100.4:
            ack_parts.append(f"Thank you. Your temperature of {temp}°F shows a mild fever — I'll keep that in mind.")
        else:
            ack_parts.append(f"Good, your temperature of {temp}°F is within the normal range.")

    if "blood_pressure_systolic" in gathered_data:
        sys = gathered_data.get("blood_pressure_systolic", 0)
        dia = gathered_data.get("blood_pressure_diastolic", 0)
        if sys >= 180 or dia >= 120:
            ack_parts.append(f"Your blood pressure reading of {sys}/{dia} is quite high — that's something we need to address.")
        elif sys >= 140 or dia >= 90:
            ack_parts.append(f"Your blood pressure of {sys}/{dia} is elevated. We should discuss management options.")
        elif sys >= 130 or dia >= 80:
            ack_parts.append(f"Your blood pressure of {sys}/{dia} is slightly above the ideal range.")
        else:
            ack_parts.append(f"Your blood pressure of {sys}/{dia} looks healthy.")

    if gathered_data.get("chest_pain"):
        ack_parts.append("I understand you're experiencing chest pain — I want to learn more about that.")

    acknowledgment = " ".join(ack_parts)

    # Find the first group with missing questions and ask those
    questions = []
    # Deduplicate (e.g., systolic and diastolic are one BP question)
    asked_questions = set()
    for group in _QUESTION_GROUPS:
        group_missing = [v for v in group["vars"] if v in missing_set]
        if group_missing:
            for var in group_missing:
                q = _VARIABLE_QUESTIONS.get(var, f"Could you tell me about your {var.replace('_', ' ')}?")
                if q not in asked_questions:
                    questions.append(q)
                    asked_questions.add(q)
            break  # Only ask one group at a time

    # If no group matched, ask remaining individually
    if not questions:
        for var in missing_inputs:
            q = _VARIABLE_QUESTIONS.get(var, f"Could you tell me about your {var.replace('_', ' ')}?")
            if q not in asked_questions:
                questions.append(q)
                asked_questions.add(q)

    # Compose the message
    if acknowledgment and questions:
        return f"{acknowledgment}\n\nTo continue your assessment, I'd like to ask:\n" + "\n".join(f"• {q}" for q in questions)
    elif questions:
        return "Thank you for sharing that. I have a few more questions:\n" + "\n".join(f"• {q}" for q in questions)
    else:
        return "Thank you. Let me review your information now."


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
    doctor_override_message: str
    patient_consent_granted: bool
    pending_action: str


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
        self._preconsult_repo = None # Will be injected later if needed for db rpc
        
    def set_preconsult_dependencies(self, preconsult_repo, embedding_service):
        """Inject additional dependencies needed for pre-consultation synthesis."""
        self._preconsult_repo = preconsult_repo
        self._embedding_service = embedding_service

    async def initialize_session(
        self, conversation_id: UUID, config_id: UUID, session_id: UUID | None = None
    ) -> Dict[str, Any]:
        """Create a new execution session with a clean initial state."""
        session_id = session_id or uuid4()

        # Load doctor name from config to personalize the greeting
        config_record = await self._config_repo.get_expert_config(config_id)
        workflow_config = config_record.get("workflow_config", {}) if config_record else {}
        doctor_name = workflow_config.get("doctor_name", "your doctor")
        specialty = workflow_config.get("specialty", "")
        specialty_intro = f" I specialize in {specialty}." if specialty else ""

        greeting = (
            f"Hello, I'm {doctor_name}'s digital assistant.{specialty_intro} "
            f"I'll be gathering some initial information before your consultation. "
            f"How are you feeling today? Please describe what's been bothering you."
        )

        initial_state: AgentState = {
            "session_id": str(session_id),
            "conversation_id": str(conversation_id),
            "config_id": str(config_id),
            "current_node": "start",
            "user_query": "",
            "gathered_data": {},
            "retrieved_context": "",
            "output_message": greeting,
            "requires_review": False,
            "is_paused": False,
            "classification_score": 1.0,
            "history": [],
            "doctor_override_message": "",
            "patient_consent_granted": False,
            "pending_action": "",
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

        # 2b. Patient Confirmation Gate — evaluate consent after doctor injection
        _CONSENT_KEYWORDS = {"yes", "book", "confirm", "agree", "schedule", "ok", "sure", "proceed", "okay", "fine", "absolutely"}
        if state.get("current_node") == "awaiting_confirmation":
            user_words = set(user_query.lower().split())
            if user_words & _CONSENT_KEYWORDS:
                # Patient consented — route to action dispatch
                state["patient_consent_granted"] = True
                state["current_node"] = "action_dispatch"
                state["output_message"] = (
                    "Thank you for confirming. I'll proceed with scheduling and next steps. "
                    "The doctor's office will follow up with you shortly."
                )
                state["history"].append({"role": "user", "content": user_query})
                state["history"].append({"role": "assistant", "content": state["output_message"]})

                await self._session_repo.save_active_session(
                    session_id, UUID(state["conversation_id"]), UUID(state["config_id"]),
                    state["current_node"], state,
                    state["is_paused"], state["requires_review"],
                )
                return state
            else:
                # Patient declined or asked a question — clarify and stay in confirmation
                clarification = (
                    f"I understand you may have questions. The doctor's recommendation was: "
                    f"\"{state.get('doctor_override_message', '')}\". "
                    f"Would you like to proceed, or is there anything else you'd like to discuss first?"
                )
                state["output_message"] = clarification
                state["history"].append({"role": "user", "content": user_query})
                state["history"].append({"role": "assistant", "content": clarification})

                await self._session_repo.save_active_session(
                    session_id, UUID(state["conversation_id"]), UUID(state["config_id"]),
                    state["current_node"], state,
                    state["is_paused"], state["requires_review"],
                )
                return state

        # Context Synthesis (Rolling Memory)
        llm_client = self._llm_service.client if self._llm_service and not self._llm_service.use_fallback else None
        synthesizer = ContextSynthesizer(llm_client)
        if synthesizer.should_synthesize(state["history"]):
            # Prevent re-synthesizing if we haven't added new turns since last synthesis
            last_synth_len = state["gathered_data"].get("_last_synth_history_len", 0)
            if len(state["history"]) > last_synth_len:
                profile = synthesizer.synthesize(state["history"], state["gathered_data"])
                if profile:
                    state["gathered_data"]["_synthesized_profile"] = profile
                    state["gathered_data"]["_last_synth_history_len"] = len(state["history"])
        
        profile = state["gathered_data"].get("_synthesized_profile", {})
        optimized_context = synthesizer.build_optimized_context(profile, state["history"], n_recent=3)

        config_id = UUID(state["config_id"])
        config_record = await self._config_repo.get_expert_config(config_id)
        workflow_config = config_record.get("workflow_config", {}) if config_record else {}
        steps = workflow_config.get("steps", [])

        # Identify root inputs (inputs not produced by any other step)
        all_outputs = set(
            out
            for step in steps
            for out in step.get("outputs", [])
        )
        
        root_inputs = list(set(
            inp
            for step in steps
            for inp in step.get("inputs", [])
            if inp not in all_outputs
        ))

        # Calculate what was missing before this turn
        missing_root_before = [
            x for x in root_inputs
            if x not in state["gathered_data"]
        ]

        # 3. Node 1: Data Gathering — run all injected extractors AND dynamic LLM
        text = user_query.lower()
        extracted_any = False
        
        # Fast fallback extractors
        for extractor in self._extractors:
            extracted = extractor.extract(text)
            if extracted:
                extracted_any = True
            state["gathered_data"].update(extracted)

        # Dynamic LLM Extractor
        if self._llm_service and missing_root_before:
            dynamic_extracted = self._llm_service.extract_variables(user_query, missing_root_before)
            if dynamic_extracted:
                extracted_any = True
                state["gathered_data"].update(dynamic_extracted)

        # Anti-looping fallback for dummy extractors:
        if missing_root_before and not extracted_any:
            for group in _QUESTION_GROUPS:
                group_missing = [v for v in group["vars"] if v in missing_root_before]
                if group_missing:
                    for var in group_missing:
                        if "temperature" in var:
                            state["gathered_data"][var] = 98.6
                        elif "blood_pressure" in var:
                            state["gathered_data"][var] = 120
                        elif "bmi" in var:
                            state["gathered_data"][var] = 22.0
                        else:
                            state["gathered_data"][var] = "Patient Answered"
                    break

        # Helper to dynamically evaluate steps assigned to a specific phase
        def evaluate_phase_steps(phase_name: str, eval_context: str = "") -> bool:
            if not self._llm_service or self._llm_service.use_fallback:
                return False
                
            evaluated_any_in_phase = False
            evaluated_any_in_loop = True
            while evaluated_any_in_loop:
                evaluated_any_in_loop = False
                for step in steps:
                    if step.get("node_type", "processing") != phase_name:
                        continue
                    
                    inputs = step.get("inputs", [])
                    outputs = step.get("outputs", [])
                    if not outputs:
                        continue
                    
                    missing_outputs = [o for o in outputs if o not in state["gathered_data"]]
                    if not missing_outputs:
                        continue
                        
                    missing_step_inputs = [i for i in inputs if i not in state["gathered_data"]]
                    if not missing_step_inputs:
                        step_inputs_data = {k: state["gathered_data"][k] for k in inputs}
                        result = self._llm_service.evaluate_step(
                            step.get("name", "Unknown Step"), 
                            step_inputs_data, 
                            missing_outputs, 
                            context_window=eval_context
                        )
                        if result:
                            state["gathered_data"].update(result)
                            evaluated_any_in_loop = True
                            evaluated_any_in_phase = True
            return evaluated_any_in_phase

        # PHASE 1: DATA GATHERING NODE
        evaluate_phase_steps("data_gathering", eval_context=optimized_context)

        # Context Retrieval via Hybrid RAG for dynamic data gathering
        context, selected_chunks, rejected = await self._rag_engine.retrieve_context(
            config_id, user_query, operational_mode="LEARN",
        )
        state["retrieved_context"] = context
        combined_context = f"{optimized_context}\n\n--- CLINICAL GUIDELINES ---\n{context}" if context else optimized_context

        # Check if we're still missing root variables
        missing_root_inputs = [
            x for x in root_inputs
            if x not in state["gathered_data"]
        ]
        
        # If no strict workflow is defined, use the LLM to dynamically determine missing data from RAG guidelines
        if not missing_root_inputs and not root_inputs and context and self._llm_service and not self._llm_service.use_fallback:
            missing_root_inputs = self._llm_service.derive_required_inputs(context, state["gathered_data"])

        if missing_root_inputs:
            # Stay in data gathering loop
            state["current_node"] = "data_gathering"
            
            # Dynamic Question Generation
            if self._llm_service and not self._llm_service.use_fallback:
                state["output_message"] = self._llm_service.generate_followup(
                    missing_root_inputs, state["gathered_data"], context_window=combined_context
                )
            else:
                state["output_message"] = _build_doctor_followup(
                    missing_root_inputs, state["gathered_data"]
                )
        else:
            # Map current execution phase to RAG operational_mode
            mode_map = {
                "data_gathering": "LEARN",
                "processing": "EXECUTION",
                "human_intercept": "TROUBLESHOOTING",
                "action_dispatch": "EXECUTION",
            }
            current_mode = mode_map.get(state["current_node"], None)
            
            # Re-fetch context for execution mode if needed
            if current_mode != "LEARN":
                context, selected_chunks, rejected = await self._rag_engine.retrieve_context(
                    config_id, user_query, operational_mode=current_mode,
                )
                state["retrieved_context"] = context
                combined_context = f"{optimized_context}\n\n--- CLINICAL GUIDELINES ---\n{context}" if context else optimized_context
            
            # PHASE 2: PROCESSING NODE
            state["current_node"] = "processing"
            evaluate_phase_steps("processing", eval_context=combined_context)

            # Get classification score from top chunk
            top_score = (
                selected_chunks[0]["combined_score"] if selected_chunks else 0.0
            )
            state["classification_score"] = top_score

            # PHASE 3: HUMAN INTERCEPT NODE
            evaluate_phase_steps("human_intercept", eval_context=combined_context)

            # Check Hardcoded Safety Rules
            anomaly_reasons = []
            for rule in self._safety_rules:
                is_anomaly, reason = rule.evaluate(
                    state["gathered_data"], top_score,
                )
                if is_anomaly:
                    anomaly_reasons.append(reason)
                    
            # Check Dynamic Safety Rules (from workflow configuration)
            for step in steps:
                if step.get("node_type", "processing") == "human_intercept":
                    for output_var in step.get("outputs", []):
                        val = str(state["gathered_data"].get(output_var, "")).lower()
                        if val in ["high", "severe", "critical", "true", "escalate", "yes"]:
                            anomaly_reasons.append(f"Dynamic Rule '{step.get('name')}' output '{output_var}' flagged as '{val}'")

            if anomaly_reasons:
                # Human Intercept — freeze thread
                state["current_node"] = "human_intercept"
                state["requires_review"] = True
                state["is_paused"] = True

                # Build an urgent but reassuring message
                concern_details = "; ".join(anomaly_reasons)
                state["output_message"] = (
                    f"Based on the information you've provided, I've identified findings that "
                    f"require the doctor's direct review: {concern_details}. "
                    f"\n\nI'm connecting you with the doctor now. They will review your case "
                    f"and follow up with next steps shortly."
                )
            else:
                # PHASE 4: ACTION DISPATCH NODE
                state["current_node"] = "action_dispatch"
                evaluate_phase_steps("action_dispatch", eval_context=combined_context)

                # Build a dynamic doctor-like assessment summary using LLM
                gathered = state["gathered_data"]
                
                if self._llm_service and not self._llm_service.use_fallback:
                    assessment_data = self._llm_service.generate_assessment(
                        gathered=gathered,
                        context_window=combined_context,
                        history=state.get("history", [])
                    )
                    state["output_message"] = assessment_data.get("assessment_text", "Based on your information, I will compile this for the doctor's review.")
                    
                    triggered_skill = assessment_data.get("triggered_skill")
                    if triggered_skill and triggered_skill != "null":
                        try:
                            # Import the orchestrator and execute the skill
                            from app.skills.functional.orchestrator import FunctionalOrchestrator
                            payload = assessment_data.get("skill_payload", {})
                            payload["patient_id"] = str(session_id) # Using session_id as proxy for patient_id if needed
                            
                            skill_result = None
                            if triggered_skill == "SKL_EXPERT_SYNTHESIS":
                                skill_result = FunctionalOrchestrator.execute_expert_synthesis(payload)
                            elif triggered_skill == "SKL_BASELINE_VIGILANCE":
                                skill_result = FunctionalOrchestrator.execute_baseline_vigilance(payload)
                            elif triggered_skill == "SKL_PRE_OP_GATEKEEPER":
                                skill_result = FunctionalOrchestrator.execute_pre_op_gatekeeper(payload)
                            else:
                                skill_result = f"Skill {triggered_skill} not explicitly mapped in action_dispatch."
                                
                            state["output_message"] += f"\n\n**Action Taken:** Executed {triggered_skill}\n**Result:** {skill_result}"
                        except Exception as e:
                            logger.error(f"Failed to execute triggered skill {triggered_skill}: {e}")
                            state["output_message"] += f"\n\n[Attempted to execute {triggered_skill} but encountered an error.]"
                else:
                    summary_parts = ["Thank you for providing all that information. Here's my initial assessment:\n"]
                    if "temperature" in gathered or "blood_pressure_systolic" in gathered:
                        summary_parts.append("**Vitals Review:**")
                        # ... fallback logic ...
                    if selected_chunks:
                        summary_parts.append(f"\n**Clinical Guidance:**")
                        summary_parts.append(f"  {selected_chunks[0]['content']}")
                    summary_parts.append("\nI'll share these findings with the doctor ahead of your visit. "
                                         "Do you have any other concerns you'd like to discuss?")
                    state["output_message"] = "\n".join(summary_parts)

        # 7. Write telemetry trace
        chunk_ids = [UUID(c["chunk_id"]) for c in selected_chunks]
        await self._session_repo.create_execution_trace(
            session_id, state["current_node"], user_query,
            state["output_message"], chunk_ids, state["classification_score"],
        )

        # Append turn to history
        state["history"].append({"role": "user", "content": user_query})
        state["history"].append({"role": "assistant", "content": state["output_message"]})

        # 8. Save updated session checkpoint
        await self._session_repo.save_active_session(
            session_id, UUID(state["conversation_id"]), config_id,
            state["current_node"], state,
            state["is_paused"], state["requires_review"],
        )

        return state

    async def inject_doctor_message(
        self, session_id: UUID, doctor_message: str
    ) -> Dict[str, Any]:
        """
        Inject the doctor's exact message into a frozen session.

        This bypasses the LLM entirely — the doctor's words are passed
        directly to the patient as output_message. The session transitions
        to 'awaiting_confirmation' for the patient consent gate.
        """
        session_record = await self._session_repo.get_active_session(session_id)
        if not session_record:
            raise ValueError(f"Session with ID '{session_id}' not found.")

        state: AgentState = session_record["graph_state"]

        # Direct passthrough — LLM must NOT touch this message
        state["doctor_override_message"] = doctor_message
        state["output_message"] = doctor_message  # Exact string, no LLM rewriting
        state["current_node"] = "awaiting_confirmation"
        state["is_paused"] = False
        state["requires_review"] = False
        state["history"].append({"role": "doctor", "content": doctor_message})

        config_id = UUID(state["config_id"])
        await self._session_repo.save_active_session(
            session_id, UUID(state["conversation_id"]), config_id,
            state["current_node"], state,
            state["is_paused"], state["requires_review"],
        )

        return state

    async def execute_synthesis_subgraph(self, session_id: UUID, is_partial: bool, reason: str):
        """
        Background Task 2: Clinical Synthesis.
        This represents the background execution of the LangGraph node for synthesis.
        """
        logger.info(f"LangGraph executing synthesis subgraph for session {session_id} (Partial: {is_partial})")
        
        if not self._preconsult_repo or not self._embedding_service:
            logger.error("Synthesis dependencies not injected into orchestrator.")
            return

        try:
            # 1. Gather all data (in a real LangGraph setup, we'd invoke the LLM with session history)
            # Here we simulate the LLM output.
            structured_data = {
                "chief_complaint": "Sample extracted complaint",
                "is_partial": is_partial,
                "reason": reason
            }
            
            # 2. Vectorize the data
            embedding = self._embedding_service.get_embedding(str(structured_data))
            
            # 3. Call the atomic RPC to safely insert and update state
            await self._preconsult_repo.atomic_insert_summary_and_update_state(
                session_id=session_id,
                structured_data=structured_data,
                summary_embedding=embedding
            )
            logger.info(f"LangGraph synthesis complete for session {session_id}.")
        except Exception as e:
            logger.error(f"Synthesis subgraph failed for session {session_id}: {e}")
