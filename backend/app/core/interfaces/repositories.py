"""
Segregated Repository Interfaces — Interface Segregation Principle (ISP)

Each interface defines a focused contract for a single domain entity.
Consumers depend only on the interface they need, not a monolithic 13-method contract.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime


class ConfigRepository(ABC):
    """
    Persistence contract for Expert Twin configuration records.
    Consumed by: ConfigService, Orchestrator (to load workflow configs).
    """

    @abstractmethod
    async def save_expert_config(
        self,
        config_id: UUID,
        expert_id: UUID,
        workflow_config: Dict[str, Any],
        active_version: str,
        is_feasible: bool,
        validation_errors: List[str],
    ) -> Dict[str, Any]:
        """Upsert an expert twin configuration record."""
        ...

    @abstractmethod
    async def get_expert_config(self, config_id: UUID) -> Optional[Dict[str, Any]]:
        """Retrieve a configuration by its ID. Returns None if not found."""
        ...

    @abstractmethod
    async def list_configs(self, expert_id: UUID) -> List[Dict[str, Any]]:
        """List all configurations for a given expert."""
        ...


class KnowledgeRepository(ABC):
    """
    Persistence contract for knowledge chunk CRUD and search operations.
    Consumed by: IngestionService, HybridRAGEngine.
    """

    @abstractmethod
    async def delete_knowledge_chunks(self, config_id: UUID) -> None:
        """Delete all knowledge chunks for a given configuration."""
        ...

    @abstractmethod
    async def save_knowledge_chunks(
        self, config_id: UUID, chunks: List[Dict[str, Any]]
    ) -> None:
        """Persist a batch of knowledge chunks for a configuration."""
        ...

    @abstractmethod
    async def match_knowledge_chunks(
        self, config_id: UUID, embedding: List[float], threshold: float, limit: int, operational_mode: str = None
    ) -> List[Dict[str, Any]]:
        """Perform vector similarity search via pgvector HNSW index, scoped by config_id."""
        ...

    @abstractmethod
    async def match_knowledge_chunks_lexical(
        self, config_id: UUID, query_text: str, threshold: float, limit: int, operational_mode: str = None
    ) -> List[Dict[str, Any]]:
        """Perform trigram-based lexical similarity search, scoped by config_id."""
        ...

    @abstractmethod
    async def get_knowledge_chunk_by_path(
        self, config_id: UUID, parent_path: str
    ) -> Optional[Dict[str, Any]]:
        """Retrieve a single knowledge chunk by its materialized path."""
        ...


class CotRepository(ABC):
    """
    Persistence contract for Chain of Thought graph nodes and edges.
    Consumed by: OnboardingService, ConfigService, UnlearningService.
    """

    @abstractmethod
    async def save_cot_nodes(
        self, config_id: UUID, nodes: List[Dict[str, Any]]
    ) -> None:
        """Persist CoT nodes for a configuration."""
        ...

    @abstractmethod
    async def get_cot_nodes(self, config_id: UUID) -> List[Dict[str, Any]]:
        """Retrieve all CoT nodes for a configuration."""
        ...

    @abstractmethod
    async def save_cot_edges(
        self, config_id: UUID, edges: List[Dict[str, Any]]
    ) -> None:
        """Persist CoT edges for a configuration."""
        ...

    @abstractmethod
    async def get_cot_edges(self, config_id: UUID) -> List[Dict[str, Any]]:
        """Retrieve all CoT edges for a configuration."""
        ...


class SessionRepository(ABC):
    """
    Persistence contract for LangGraph session state checkpointing
    and execution telemetry traces.
    Consumed by: ZeroTrustOrchestrator.
    """

    @abstractmethod
    async def get_active_session(
        self, session_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Retrieve a session checkpoint by ID. Returns None if not found."""
        ...

    @abstractmethod
    async def save_active_session(
        self,
        session_id: UUID,
        conversation_id: UUID,
        config_id: UUID,
        current_node: str,
        graph_state: Dict[str, Any],
        is_paused: bool,
        requires_review: bool,
    ) -> Dict[str, Any]:
        """Upsert a session state checkpoint."""
        ...

    @abstractmethod
    async def create_execution_trace(
        self,
        session_id: UUID,
        step_name: str,
        prompt_used: str,
        response_generated: str,
        retrieved_chunk_ids: List[UUID],
        classification_score: float,
    ) -> Dict[str, Any]:
        """Write an immutable execution trace to the telemetry ledger."""
        ...


class WorkflowRepository(ABC):
    """Persistence contract for expert_workflows and workflow_tasks."""
    
    @abstractmethod
    async def get_workflow(self, workflow_id: UUID) -> Optional[Dict[str, Any]]:
        ...

    @abstractmethod
    async def get_workflow_tasks(self, workflow_id: UUID) -> List[Dict[str, Any]]:
        ...

    @abstractmethod
    async def get_task_by_step(self, workflow_id: UUID, step_number: int) -> Optional[Dict[str, Any]]:
        ...

    @abstractmethod
    async def create_workflow(self, config_id: UUID, expert_id: str, workflow_name: str) -> Dict[str, Any]:
        ...

    @abstractmethod
    async def create_workflow_tasks(self, workflow_id: UUID, tasks: List[Dict[str, Any]]) -> None:
        ...


class ThresholdRepository(ABC):
    """Persistence contract for entity_thresholds."""
    
    @abstractmethod
    async def get_thresholds_for_expert(self, expert_id: str) -> List[Dict[str, Any]]:
        ...

    @abstractmethod
    async def get_threshold_by_entity(self, expert_id: str, entity_name: str) -> Optional[Dict[str, Any]]:
        ...

    @abstractmethod
    async def save_thresholds(self, config_id: UUID, expert_id: str, thresholds: List[Dict[str, Any]]) -> None:
        ...


class PreConsultRepository(ABC):
    """
    Persistence contract for Pre-Consultation Workflow.
    """

    @abstractmethod
    async def create_session(
        self, patient_id: UUID, config_id: UUID, workflow_id: UUID, configuration_snapshot: Dict[str, Any]
    ) -> Dict[str, Any]:
        ...

    @abstractmethod
    async def get_session(self, session_id: UUID) -> Optional[Dict[str, Any]]:
        ...

    @abstractmethod
    async def update_session_state(
        self, 
        session_id: UUID, 
        status: str, 
        confidence_score: float, 
        increment_turn: bool = False,
        current_entities: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        ...

    @abstractmethod
    async def append_interaction_log(
        self, 
        session_id: UUID, 
        sender_type: str, 
        message_text: str, 
        extracted_entities: Dict[str, Any], 
        turn_index: int
    ) -> Dict[str, Any]:
        ...

    @abstractmethod
    async def get_interaction_logs(self, session_id: UUID) -> List[Dict[str, Any]]:
        ...

    @abstractmethod
    async def atomic_insert_summary_and_update_state(
        self, 
        session_id: UUID, 
        structured_data: Dict[str, Any], 
        summary_embedding: List[float]
    ) -> None:
        """Calls the atomic database RPC to insert the summary and update state safely."""
        ...
        
    @abstractmethod
    async def get_active_sessions(self) -> List[Dict[str, Any]]:
        """Retrieve all sessions currently in active states (GATHERING, SYNTHESIZING, etc.)."""
        ...
