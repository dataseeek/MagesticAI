"""Backward compatibility shim — re-exports from providers.gemini."""
from providers.gemini import GeminiCLIProvider  # noqa: F401

__all__ = ["GeminiCLIProvider"]
