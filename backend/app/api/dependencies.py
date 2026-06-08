"""
Dependency Injection Container — Dependency Inversion Principle (DIP)

Centralizes all service wiring in one place. Routes depend on abstractions
injected via FastAPI's Depends() system, never on concrete implementations.

Design: App-level singletons with a ServiceProvider class that supports
future dynamic reconfiguration (hot-swapping repos, embedding services, etc.)
without restarting the application.
"""
from typing import List
import logging

from backend.app.core.config import settings

# Interface imports
from backend.app.core.interfaces.repositories import (
    ConfigRepository,
    KnowledgeRepository,
    CotRepository,
    SessionRepository,
    PreConsultRepository,
)
from backend.app.core.interfaces.embedding import EmbeddingService
from backend.app.core.interfaces.export import ExportService

# Concrete implementations
from backend.app.repositories.supabase_config_repo import SupabaseConfigRepository
from backend.app.repositories.supabase_knowledge_repo import SupabaseKnowledgeRepository
from backend.app.repositories.supabase_cot_repo import SupabaseCotRepository
from backend.app.repositories.supabase_session_repo import SupabaseSessionRepository
from backend.app.repositories.supabase_preconsult_repo import SupabasePreConsultRepository
from backend.app.services.embedding.gemini_embedder import GeminiEmbeddingService
from backend.app.services.export.obsidian_export import ObsidianExportService

# Services
from backend.app.services.config_service import ConfigService
from backend.app.services.unlearning_service import UnlearningService
from backend.app.services.ingestion_service import StructuralRAGIngestionPipeline
from backend.app.services.hybrid_rag_service import HybridRAGEngine
from backend.app.services.preconsult_service import PreConsultationService
from backend.app.orchestrator.state_machine import ZeroTrustOrchestrator

# Extractors & Safety Rules
from backend.app.orchestrator.extractors.base import DataExtractor
from backend.app.orchestrator.extractors.vitals_extractor import VitalsExtractor
from backend.app.orchestrator.extractors.symptom_extractor import SymptomExtractor
from backend.app.orchestrator.safety_rules.base import SafetyRule
from backend.app.orchestrator.safety_rules.fever_rule import FeverSafetyRule
from backend.app.orchestrator.safety_rules.cardiac_rule import CardiacSafetyRule
from backend.app.orchestrator.safety_rules.confidence_rule import ConfidenceSafetyRule

logger = logging.getLogger(__name__)


class ServiceProvider:
    """
    Centralized service provider with app-level singletons.

    Designed for future dynamic reconfiguration:
    - Call reconfigure_repositories() to hot-swap DB backends
    - Call reconfigure_embedding() to switch embedding models
    - All dependent services automatically pick up changes via references

    Thread-safety note: For production multi-worker deployments,
    add locking around reconfigure methods.
    """

    def __init__(self):
        self._initialized = False

        # Repository singletons
        self._config_repo: ConfigRepository | None = None
        self._knowledge_repo: KnowledgeRepository | None = None
        self._cot_repo: CotRepository | None = None
        self._session_repo: SessionRepository | None = None
        self._preconsult_repo: PreConsultRepository | None = None

        # Service singletons
        self._embedding_service: EmbeddingService | None = None
        self._export_service: ExportService | None = None
        self._rag_engine: HybridRAGEngine | None = None
        self._config_service: ConfigService | None = None
        self._unlearning_service: UnlearningService | None = None
        self._ingestion_pipeline: StructuralRAGIngestionPipeline | None = None
        self._orchestrator: ZeroTrustOrchestrator | None = None
        self._preconsult_service: PreConsultationService | None = None

        # Pluggable extractors and safety rules
        self._extractors: List[DataExtractor] | None = None
        self._safety_rules: List[SafetyRule] | None = None

    def initialize(self) -> None:
        """
        Initialize all singletons. Called once at app startup.
        Subsequent calls are idempotent.
        """
        if self._initialized:
            return

        logger.info("Initializing ServiceProvider singletons...")

        # 1. Repositories
        self._config_repo = SupabaseConfigRepository(
            settings.SUPABASE_URL, settings.SUPABASE_KEY
        )
        self._knowledge_repo = SupabaseKnowledgeRepository(
            settings.SUPABASE_URL, settings.SUPABASE_KEY
        )
        self._cot_repo = SupabaseCotRepository(
            settings.SUPABASE_URL, settings.SUPABASE_KEY
        )
        self._session_repo = SupabaseSessionRepository(
            settings.SUPABASE_URL, settings.SUPABASE_KEY
        )
        self._preconsult_repo = SupabasePreConsultRepository(
            settings.SUPABASE_URL, settings.SUPABASE_KEY
        )

        # 2. Infrastructure services
        self._embedding_service = GeminiEmbeddingService(
            settings.GEMINI_API_KEY
        )
        self._export_service = ObsidianExportService(settings.OBSIDIAN_VAULT_PATH)

        # 3. Pluggable extractors (Open/Closed — add new ones here)
        self._extractors = [
            VitalsExtractor(),
            SymptomExtractor(),
        ]

        # 4. Pluggable safety rules (Open/Closed — add new ones here)
        self._safety_rules = [
            FeverSafetyRule(),
            CardiacSafetyRule(),
            ConfidenceSafetyRule(confidence_gate=0.85),
        ]

        # 5. Business services (composed from repositories + infra)
        self._rag_engine = HybridRAGEngine(
            self._knowledge_repo, self._embedding_service
        )
        self._config_service = ConfigService(
            self._config_repo, self._cot_repo, self._export_service
        )
        self._unlearning_service = UnlearningService(
            self._config_repo, self._cot_repo, self._export_service
        )
        self._ingestion_pipeline = StructuralRAGIngestionPipeline(
            self._knowledge_repo, self._embedding_service
        )
        self._orchestrator = ZeroTrustOrchestrator(
            config_repo=self._config_repo,
            session_repo=self._session_repo,
            rag_engine=self._rag_engine,
            extractors=self._extractors,
            safety_rules=self._safety_rules,
        )
        self._orchestrator.set_preconsult_dependencies(self._preconsult_repo, self._embedding_service)

        self._preconsult_service = PreConsultationService(
            preconsult_repo=self._preconsult_repo,
            safety_rules=self._safety_rules,
            langgraph_orchestrator=self._orchestrator
        )

        self._initialized = True
        logger.info("ServiceProvider initialization complete.")

    # --- Accessor methods for FastAPI Depends() ---

    @property
    def config_repo(self) -> ConfigRepository:
        return self._config_repo

    @property
    def knowledge_repo(self) -> KnowledgeRepository:
        return self._knowledge_repo

    @property
    def cot_repo(self) -> CotRepository:
        return self._cot_repo

    @property
    def session_repo(self) -> SessionRepository:
        return self._session_repo

    @property
    def preconsult_repo(self) -> PreConsultRepository:
        return self._preconsult_repo

    @property
    def embedding_service(self) -> EmbeddingService:
        return self._embedding_service

    @property
    def export_service(self) -> ExportService:
        return self._export_service

    @property
    def rag_engine(self) -> HybridRAGEngine:
        return self._rag_engine

    @property
    def config_service(self) -> ConfigService:
        return self._config_service

    @property
    def unlearning_service(self) -> UnlearningService:
        return self._unlearning_service

    @property
    def ingestion_pipeline(self) -> StructuralRAGIngestionPipeline:
        return self._ingestion_pipeline

    @property
    def orchestrator(self) -> ZeroTrustOrchestrator:
        return self._orchestrator

    @property
    def preconsult_service(self) -> PreConsultationService:
        return self._preconsult_service


# --- Module-level singleton ---
provider = ServiceProvider()


# --- FastAPI Depends() functions ---
# These return interface types, not concrete implementations.

def get_config_repo() -> ConfigRepository:
    return provider.config_repo


def get_knowledge_repo() -> KnowledgeRepository:
    return provider.knowledge_repo


def get_cot_repo() -> CotRepository:
    return provider.cot_repo


def get_session_repo() -> SessionRepository:
    return provider.session_repo


def get_embedding_service() -> EmbeddingService:
    return provider.embedding_service


def get_export_service() -> ExportService:
    return provider.export_service


def get_rag_engine() -> HybridRAGEngine:
    return provider.rag_engine


def get_config_service() -> ConfigService:
    return provider.config_service



def get_unlearning_service() -> UnlearningService:
    return provider.unlearning_service


def get_ingestion_pipeline() -> StructuralRAGIngestionPipeline:
    return provider.ingestion_pipeline


def get_orchestrator() -> ZeroTrustOrchestrator:
    return provider.orchestrator

def get_preconsult_service() -> PreConsultationService:
    return provider.preconsult_service

