"""
base_adapter.py — Abstract Domain Adapter Contract
====================================================
Every domain-specific adapter MUST implement this interface.

RULE: The Universal Core (pipeline.py, nodes/) must NEVER import from adapters/.
      Adapters are injected at the API boundary and travel inside GraphState.
"""
from abc import ABC, abstractmethod


class BaseDomainAdapter(ABC):
    """
    Abstract base class for all domain adapters.
    Each adapter encodes the immutable rules and identity metadata
    for one specific domain + role combination (e.g., Healthcare / Doctor).
    """

    @abstractmethod
    def get_domain_id(self) -> str:
        """
        Returns the UUID of the Domain record in the `domains` table.
        Used as a FK when writing to expert_dna, master_cases, etc.
        """
        ...

    @abstractmethod
    def get_role_id(self) -> str:
        """
        Returns the UUID of the Role record in the `roles` table.
        Used as a FK when writing to expert_dna, master_cases, etc.
        """
        ...

    @abstractmethod
    def get_domain_name(self) -> str:
        """Human-readable domain name (e.g., 'Healthcare')."""
        ...

    @abstractmethod
    def get_role_name(self) -> str:
        """Human-readable role name (e.g., 'Doctor')."""
        ...

    @abstractmethod
    def get_system_prompt(self) -> str:
        """
        Returns the IMMUTABLE domain safety rules injected as the first
        layer of every LLM system prompt. These rules cannot be overridden
        by persona data or user input.
        """
        ...

    @abstractmethod
    def get_fallback_identity(self) -> str:
        """
        Returns the name of the fallback persona used when the RAG
        confidence score falls below the threshold (hat-switching).
        E.g., 'Duty Nurse', 'Scrum Master', 'Teaching Assistant'.
        """
        ...

    @abstractmethod
    def get_confidence_threshold(self) -> float:
        """
        Returns the minimum cosine similarity score required for the system
        to answer AS the primary expert (rather than escalating or falling back).
        This is a tunable hyperparameter, NOT a hardcoded value.
        """
        ...

    def get_semantic_markers(self) -> list[str]:
        """
        Returns regex strings used to identify ambiguous or soft rules in the text.
        """
        return [r"\btypically\b", r"\bgenerally\b", r"\busually\b"]

    def to_context_dict(self) -> dict:
        """
        Serialises the adapter's metadata into a plain dict so it can be
        stored inside GraphState (which must remain JSON-serialisable).
        """
        return {
            "domain_id":            self.get_domain_id(),
            "role_id":              self.get_role_id(),
            "domain_name":          self.get_domain_name(),
            "role_name":            self.get_role_name(),
            "expert_role":          self.get_role_name(),
            "fallback_identity":    self.get_fallback_identity(),
            "confidence_threshold": self.get_confidence_threshold(),
            "semantic_markers":     self.get_semantic_markers(),
        }
