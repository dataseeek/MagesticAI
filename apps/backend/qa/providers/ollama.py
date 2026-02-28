"""Backward compatibility shim — re-exports from providers.ollama."""
from providers.ollama import OllamaProvider  # noqa: F401

__all__ = ["OllamaProvider"]
