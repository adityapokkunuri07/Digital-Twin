"""
Data Extractor ABC — Open/Closed Principle.

Defines the contract for pluggable data extraction strategies.
New extractors (lab results, imaging data, etc.) can be added
without modifying the state machine core.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any


class DataExtractor(ABC):
    """
    Abstract contract for extracting structured data from user input text.
    Each extractor is responsible for one category of data extraction.
    """

    @abstractmethod
    def extract(self, text: str) -> Dict[str, Any]:
        """
        Parse the input text and extract relevant key-value pairs.

        Args:
            text: Lowercased user input text.

        Returns:
            Dictionary of extracted variable names to values.
            Empty dict if nothing relevant is found.
        """
        ...
