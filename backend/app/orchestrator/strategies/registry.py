"""
Strategy Registry — Resolves strategy identifiers to concrete ProcessingStrategy instances.
"""
from typing import Dict
from backend.app.orchestrator.strategies.base import ProcessingStrategy


class StrategyRegistry:
    """
    Registry for dynamic mapping of `strategy_identifier` to concrete processors.
    Enforces the Open/Closed Principle.
    """
    
    _strategies: Dict[str, ProcessingStrategy] = {}
    
    @classmethod
    def register(cls, identifier: str, strategy: ProcessingStrategy) -> None:
        """Register a strategy implementation under a string identifier."""
        cls._strategies[identifier] = strategy
        
    @classmethod
    def resolve(cls, identifier: str) -> ProcessingStrategy:
        """
        Resolve an identifier to its strategy instance.
        
        Args:
            identifier: The strategy string (e.g., 'SYMPTOM_PARSER').
            
        Returns:
            The concrete ProcessingStrategy instance.
            
        Raises:
            KeyError: If the strategy identifier is unknown.
        """
        if identifier not in cls._strategies:
            raise KeyError(f"Unknown processing strategy identifier: '{identifier}'. "
                           f"Registered strategies: {list(cls._strategies.keys())}")
        return cls._strategies[identifier]
