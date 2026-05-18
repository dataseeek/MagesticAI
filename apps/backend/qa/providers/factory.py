"""
QA LLM Provider Factory — Backward compatibility shim
=======================================================

Delegates to ``providers.factory`` which now contains the canonical
implementations.  All existing imports continue to work unchanged.
"""

from providers.factory import (  # noqa: F401
    _PROVIDER_ALIASES,
    get_qa_llm_provider,
    list_provider_aliases,
    list_providers,
)
from providers.factory import (
    _TEXT_REGISTRY as _PROVIDER_REGISTRY,
)

__all__ = [
    "get_qa_llm_provider",
    "list_providers",
    "list_provider_aliases",
    "_PROVIDER_ALIASES",
    "_PROVIDER_REGISTRY",
]
