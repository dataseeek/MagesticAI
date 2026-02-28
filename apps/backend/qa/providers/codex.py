"""Backward compatibility shim — re-exports from providers.codex."""
from providers.codex import CodexCLIProvider  # noqa: F401

__all__ = ["CodexCLIProvider"]
