# adapters/__init__.py
from .base_adapter import BaseDomainAdapter
from .domain_router import get_adapter, VALID_DOMAINS, VALID_ROLES

__all__ = ["BaseDomainAdapter", "get_adapter", "VALID_DOMAINS", "VALID_ROLES"]
