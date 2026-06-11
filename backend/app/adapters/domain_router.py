"""
domain_router.py — Domain Adapter Factory
==========================================
Resolves a (domain, role) string pair into the correct BaseDomainAdapter
instance. This is the ONLY place the application knows which adapter maps
to which domain/role string. All API endpoints call get_adapter() once,
then operate exclusively through the adapter interface.
"""
from .base_adapter import BaseDomainAdapter
from .healthcare_adapter import HealthcareAdapter
from .it_adapter import ITAdapter
from .education_adapter import EducationAdapter

# ── Supported domain/role combinations ────────────────────────────────────────
# Key format: "domain:role" (lowercased, underscored)
_ADAPTER_REGISTRY: dict[str, BaseDomainAdapter] = {
    "healthcare:doctor":          HealthcareAdapter(),
    "it:project_manager":         ITAdapter(),
    "education:tutor":            EducationAdapter(),
}

# ── Valid enum values exposed for FastAPI Query validation ─────────────────────
VALID_DOMAINS = ["healthcare", "it", "education"]
VALID_ROLES   = ["doctor", "project_manager", "tutor"]


def get_adapter(domain: str, role: str) -> BaseDomainAdapter:
    """
    Resolves a domain + role pair to the correct adapter instance.

    Args:
        domain: One of 'healthcare', 'it', 'education'
        role:   One of 'doctor', 'project_manager', 'tutor'

    Returns:
        The matching BaseDomainAdapter instance.

    Raises:
        ValueError if the domain/role combination is not registered.
    """
    key = f"{domain.lower().strip()}:{role.lower().strip()}"
    adapter = _ADAPTER_REGISTRY.get(key)
    if not adapter:
        raise ValueError(
            f"No adapter registered for domain='{domain}', role='{role}'. "
            f"Valid combinations: {list(_ADAPTER_REGISTRY.keys())}"
        )
    return adapter
