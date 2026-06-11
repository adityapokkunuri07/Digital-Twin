"""
base_skill.py — Base class for all functional skills
=====================================================
All functional skills inherit from this base class.
It enforces a consistent interface: skill_name() + execute().
"""
from typing import Dict, Any
from abc import ABC, abstractmethod


class BaseFunctionalSkill(ABC):
    """
    Abstract base class for all IT (and other domain) functional skills.
    Every skill must implement:
      - skill_name(): returns the skill's unique string identifier
      - execute(payload): runs the skill and returns a result dict
    """

    @staticmethod
    @abstractmethod
    def skill_name() -> str:
        """Return the unique skill name, e.g. 'SKL_IT_ARCH_DRIFT'."""
        ...

    @staticmethod
    @abstractmethod
    def execute(payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the skill with the given payload.
        Returns a result dictionary.
        """
        ...
