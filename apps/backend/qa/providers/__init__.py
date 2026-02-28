"""
QA LLM Provider Abstraction Layer
===================================

Defines the minimal interface (``BaseLLMProvider``) that any LLM backend must
satisfy to replace ``ClaudeSDKClient`` inside ``run_qa_agent_session()`` and
``run_qa_fixer_session()``.

Derived from the usage audit documented in:
  .magestic-ai/specs/004-add-alternative-llm-for-qa-rev/abstraction_boundary.md

Minimal interface
-----------------
Callers (``reviewer.py`` / ``fixer.py``) consume exactly **two methods** plus
the **async context manager** protocol:

1. ``query(prompt: str) -> None``
   Send the initial prompt and start the response stream.

2. ``receive_response() -> AsyncIterator[Any]``
   Stream back structured message objects.  Each object is inspected
   *only* via ``type(msg).__name__`` string comparisons — no ``isinstance``
   calls — so adapters must yield objects whose class names match exactly:

   Top-level: ``AssistantMessage``, ``UserMessage``
   Blocks:    ``TextBlock``, ``ToolUseBlock``, ``ToolResultBlock``

   The canonical implementations of these wrapper types are in
   ``qa.providers.types``.

3. Async context manager (``__aenter__`` / ``__aexit__``)
   ``loop.py`` always wraps clients in ``async with client:`` for
   resource management.

Package layout
--------------
    qa/providers/
        __init__.py   — BaseLLMProvider ABC (this file)
        types.py      — Shared message-protocol wrapper classes
        claude.py     — ClaudeProvider   (wraps ClaudeSDKClient)
        codex.py      — CodexCLIProvider (Codex CLI adapter)
        gemini.py     — GeminiCLIProvider (Gemini CLI adapter)
        ollama.py     — OllamaProvider   (local Ollama adapter)
        factory.py    — get_qa_llm_provider() factory function

Usage::

    from qa.providers import get_qa_llm_provider

    provider = get_qa_llm_provider("gemini", model="gemini-2.0-flash")
    async with provider:
        await provider.query(prompt)
        async for msg in provider.receive_response():
            ...
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator, Any

from .types import (
    AssistantMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)

# ---------------------------------------------------------------------------
# Abstract base class
# ---------------------------------------------------------------------------


class BaseLLMProvider(ABC):
    """
    Minimal interface every QA LLM provider adapter must satisfy.

    Derived from the usage pattern in:
    - apps/backend/qa/reviewer.py::run_qa_agent_session()
    - apps/backend/qa/fixer.py::run_qa_fixer_session()
    - apps/backend/qa/loop.py (async context manager usage)

    Concrete implementations live in the sibling modules:
    - ``qa.providers.claude``  — wraps ClaudeSDKClient (default)
    - ``qa.providers.codex``   — Codex CLI
    - ``qa.providers.gemini``  — Gemini CLI
    - ``qa.providers.ollama``  — local Ollama / any OpenAI-compatible endpoint

    All provider adapters must yield message objects whose *class names*
    match exactly what ``reviewer.py`` / ``fixer.py`` expect.  Use the
    wrapper types from ``qa.providers.types`` for this purpose.
    """

    # ------------------------------------------------------------------
    # 1. query() — send the initial prompt to the LLM
    # ------------------------------------------------------------------

    @abstractmethod
    async def query(self, prompt: str) -> None:
        """Send a prompt to the LLM to start a response stream.

        Args:
            prompt: The system + user prompt string (may be several kB).

        Returns:
            None.  The return value is never inspected by callers.

        Raises:
            Exception: Any exception propagates to the outer try/except in
                ``run_qa_agent_session()`` and is returned as "error" status.
        """

    # ------------------------------------------------------------------
    # 2. receive_response() — stream back structured messages
    # ------------------------------------------------------------------

    @abstractmethod
    def receive_response(self) -> AsyncIterator[Any]:
        """Return an async iterable of message objects produced by the LLM.

        Each yielded object is inspected *only* via:
          - ``type(msg).__name__``   (string comparison, never isinstance)
          - ``hasattr(msg, attr)``   (attribute presence check)
          - ``getattr(msg, attr)``   (attribute value access)

        Callers consume the stream as::

            async for msg in provider.receive_response():
                msg_type = type(msg).__name__
                if msg_type == "AssistantMessage":
                    ...

        Use the canonical wrapper types from ``qa.providers.types`` to
        ensure class names match exactly what reviewers.py / fixer.py expect.

        Yields:
            Message objects — typically ``AssistantMessage`` or
            ``UserMessage`` instances (or protocol-compatible equivalents).
        """

    # ------------------------------------------------------------------
    # 3. Async context manager — loop.py wraps every client in async with
    # ------------------------------------------------------------------

    @abstractmethod
    async def __aenter__(self) -> "BaseLLMProvider":
        """Enter the provider context (connect, initialise session, etc.).

        Returns:
            self — so callers can use ``async with provider as p:``
        """

    @abstractmethod
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit the provider context (disconnect, cleanup, etc.)."""


# ---------------------------------------------------------------------------
# Factory (imported after BaseLLMProvider to avoid circular imports)
# ---------------------------------------------------------------------------

# factory.py references BaseLLMProvider only under TYPE_CHECKING, so this
# deferred import is safe regardless of which module was loaded first.
from .factory import get_qa_llm_provider, list_provider_aliases, list_providers  # noqa: E402

# ---------------------------------------------------------------------------
# Re-export public symbols
# ---------------------------------------------------------------------------

__all__ = [
    # Abstract base
    "BaseLLMProvider",
    # Message protocol types (convenience re-export)
    "AssistantMessage",
    "TextBlock",
    "ToolUseBlock",
    "ToolResultBlock",
    "UserMessage",
    # Factory
    "get_qa_llm_provider",
    "list_providers",
    "list_provider_aliases",
]
