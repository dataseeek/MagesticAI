"""Backward compatibility shim — re-exports from providers.claude."""
from providers.claude import ClaudeProvider  # noqa: F401

__all__ = ["ClaudeProvider"]
