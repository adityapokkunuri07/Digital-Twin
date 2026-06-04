"""
Base Repository — Shared Supabase client initialization.

Provides a common base for all Supabase repository implementations,
handling client creation and mock-mode fallback logic in a single place (DRY).

Designed with future dynamic swapping in mind — the client can be
replaced at runtime via the `reconfigure()` method without restarting the app.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class SupabaseClientMixin:
    """
    Mixin providing shared Supabase client initialization and mock-mode detection.

    All repository implementations inherit from this to avoid duplicating
    connection setup logic across 4 separate repo classes.
    """

    def __init__(self, url: str = "", key: str = ""):
        self._url = url
        self._key = key
        self._client = None
        self._use_mock = True
        self._initialize_client(url, key)

    def _initialize_client(self, url: str, key: str) -> None:
        """Attempt to create a Supabase client. Falls back to mock mode on failure."""
        if url and key:
            try:
                from supabase import create_client
                self._client = create_client(url, key)
                self._use_mock = False
                logger.info("Supabase client initialized successfully.")
            except ImportError:
                logger.warning(
                    "Supabase package not installed. Falling back to mock database."
                )
            except Exception as e:
                logger.error(
                    f"Failed to connect to Supabase: {e}. Falling back to mock database."
                )

        if self._use_mock:
            logger.info("Repository running in Mock Database mode.")

    def reconfigure(self, url: str, key: str) -> None:
        """
        Hot-swap the Supabase client at runtime.
        Designed for future dynamic configuration changes without app restart.
        """
        self._initialize_client(url, key)

    @property
    def client(self):
        """Access the underlying Supabase client. None in mock mode."""
        return self._client

    @property
    def use_mock(self) -> bool:
        """Whether the repository is operating in mock (in-memory) mode."""
        return self._use_mock
