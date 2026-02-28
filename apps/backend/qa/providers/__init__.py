"""
QA LLM Provider — Backward compatibility shim
================================================

This package re-exports everything from the top-level ``providers`` package.
All provider implementations have been promoted to ``providers/`` to support
multi-phase usage (not just QA).

Existing imports like ``from qa.providers import BaseLLMProvider`` and
``from qa.providers import get_qa_llm_provider`` continue to work unchanged.
"""

from providers import *  # noqa: F401, F403
from providers import __all__  # noqa: F401
