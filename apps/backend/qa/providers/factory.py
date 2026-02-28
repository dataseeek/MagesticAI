"""
QA LLM Provider Factory
========================

Single entry-point for instantiating a ``BaseLLMProvider`` by name.

Usage::

    from qa.providers.factory import get_qa_llm_provider

    # Default Claude provider
    provider = get_qa_llm_provider(
        "claude",
        project_dir=project_dir,
        spec_dir=spec_dir,
        model="claude-opus-4-5",
    )

    # Gemini CLI provider
    provider = get_qa_llm_provider("gemini", model="gemini-2.0-flash")

    # Codex CLI provider
    provider = get_qa_llm_provider("codex", model="o4-mini")

    # Local Ollama provider
    provider = get_qa_llm_provider("ollama", model="llama3.2")

    # Then use the provider uniformly:
    async with provider:
        await provider.query(prompt)
        async for msg in provider.receive_response():
            ...

Supported provider names (case-insensitive)
--------------------------------------------
+------------+-------------------------------+-----------------------------------------------+
| Name       | Class                         | Key kwargs                                    |
+============+===============================+===============================================+
| ``claude`` | :class:`~.claude.ClaudeProvider`    | ``project_dir``, ``spec_dir``, ``model``,   |
|            |                               | ``agent_type``, ``max_thinking_tokens``, …    |
+------------+-------------------------------+-----------------------------------------------+
| ``codex``  | :class:`~.codex.CodexCLIProvider`   | ``model``, ``codex_path``, ``timeout``,     |
|            |                               | ``working_dir``, ``extra_args``               |
+------------+-------------------------------+-----------------------------------------------+
| ``gemini`` | :class:`~.gemini.GeminiCLIProvider` | ``model``, ``gemini_path``, ``timeout``,    |
|            |                               | ``working_dir``, ``extra_args``               |
+------------+-------------------------------+-----------------------------------------------+
| ``ollama`` | :class:`~.ollama.OllamaProvider`    | ``model``, ``base_url``, ``timeout``,       |
|            |                               | ``extra_options``                             |
+------------+-------------------------------+-----------------------------------------------+

Any ``**kwargs`` not recognised by the target constructor will cause a
``TypeError`` at instantiation time — fail-fast behaviour is intentional.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from qa.providers import BaseLLMProvider

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Registry: maps lowercase provider names -> import path + class name
# ---------------------------------------------------------------------------

# Using lazy imports (strings) to avoid importing all provider modules at
# package load time.  Each provider has optional heavy dependencies
# (e.g. claude_agent_sdk) that should only be resolved when actually used.

_PROVIDER_REGISTRY: dict[str, tuple[str, str]] = {
    "claude": ("qa.providers.claude", "ClaudeProvider"),
    "codex": ("qa.providers.codex", "CodexCLIProvider"),
    "gemini": ("qa.providers.gemini", "GeminiCLIProvider"),
    "ollama": ("qa.providers.ollama", "OllamaProvider"),
}

# Human-readable aliases (normalised to the canonical names above)
_PROVIDER_ALIASES: dict[str, str] = {
    "claude": "claude",
    "claude-sdk": "claude",
    "anthropic": "claude",
    "codex": "codex",
    "codex-cli": "codex",
    "openai-codex": "codex",
    "gemini": "gemini",
    "gemini-cli": "gemini",
    "google": "gemini",
    "ollama": "ollama",
    "local": "ollama",
    "local-ollama": "ollama",
}


def get_qa_llm_provider(provider_name: str, **kwargs: Any) -> BaseLLMProvider:
    """Instantiate and return a ``BaseLLMProvider`` by name.

    This is the primary entry-point for the QA loop (``loop.py``) and any
    other caller that needs to create a QA LLM provider based on a
    user-facing setting string.

    Args:
        provider_name: Case-insensitive provider identifier.  Recognised
            values: ``"claude"``, ``"codex"`` (or ``"codex-cli"``),
            ``"gemini"`` (or ``"gemini-cli"``), ``"ollama"`` (or
            ``"local"``).  See the module docstring for the full alias
            table.
        **kwargs: Keyword arguments forwarded verbatim to the provider's
            ``__init__``.  Each provider accepts different parameters —
            refer to the individual provider module docstrings for details.

    Returns:
        A concrete :class:`~qa.providers.BaseLLMProvider` instance that
        has **not** yet entered its async context.  Call
        ``async with provider:`` before invoking ``query()`` /
        ``receive_response()``.

    Raises:
        ValueError: If *provider_name* is not a recognised provider key or
            alias.
        TypeError: If **kwargs** contains parameters not accepted by the
            chosen provider's ``__init__``.
        ImportError: If the provider module cannot be imported (e.g. a
            required dependency is missing).

    Examples::

        from pathlib import Path
        from qa.providers.factory import get_qa_llm_provider

        # Claude (default) — needs project_dir and spec_dir
        claude = get_qa_llm_provider(
            "claude",
            project_dir=Path("/my/project"),
            spec_dir=Path("/my/project/.magestic-ai/specs/001-feature"),
            model="claude-opus-4-5",
        )

        # Gemini CLI — only needs model (optional)
        gemini = get_qa_llm_provider("gemini", model="gemini-2.0-flash")

        # Ollama — target a specific local model
        ollama = get_qa_llm_provider("ollama", model="codellama:13b")
    """
    normalised = provider_name.strip().lower()

    # Resolve alias to canonical name
    canonical = _PROVIDER_ALIASES.get(normalised)
    if canonical is None:
        known = sorted(_PROVIDER_ALIASES.keys())
        raise ValueError(
            f"Unknown QA LLM provider: {provider_name!r}. "
            f"Supported values: {known}"
        )

    module_path, class_name = _PROVIDER_REGISTRY[canonical]

    logger.debug(
        "get_qa_llm_provider: creating provider canonical=%r class=%s kwargs_keys=%s",
        canonical,
        class_name,
        list(kwargs.keys()),
    )

    # Lazy import — resolve the provider class at call time
    try:
        import importlib
        module = importlib.import_module(module_path)
    except ImportError as exc:
        raise ImportError(
            f"Failed to import provider module '{module_path}' for "
            f"provider '{provider_name}': {exc}"
        ) from exc

    provider_cls = getattr(module, class_name)

    # Instantiate — any unrecognised kwargs surface as TypeError here
    instance: BaseLLMProvider = provider_cls(**kwargs)

    logger.debug(
        "get_qa_llm_provider: created %s instance", class_name
    )

    return instance


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------


def list_providers() -> list[str]:
    """Return a sorted list of all recognised canonical provider names.

    Useful for populating dropdown menus in the settings UI.

    Returns:
        A list of canonical provider name strings, e.g.
        ``["claude", "codex", "gemini", "ollama"]``.
    """
    return sorted(_PROVIDER_REGISTRY.keys())


def list_provider_aliases() -> dict[str, str]:
    """Return a copy of the full alias-to-canonical mapping.

    Returns:
        A dict mapping every accepted alias (including canonical names) to
        its canonical provider name.
    """
    return dict(_PROVIDER_ALIASES)


__all__ = [
    "get_qa_llm_provider",
    "list_providers",
    "list_provider_aliases",
]
