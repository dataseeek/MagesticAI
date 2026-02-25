"""
Provider registry — singleton instances and concurrent detection.
"""

import asyncio
import logging

from .base import ProviderInfo, ProviderStrategy
from .claude_provider import ClaudeProvider
from .codex_provider import CodexProvider
from .gemini_provider import GeminiProvider
from .ollama_provider import OllamaProvider
from .openai_compat_provider import OpenAICompatProvider

logger = logging.getLogger(__name__)

# Singleton provider instances
_providers: dict[str, ProviderStrategy] = {}


def _init_providers() -> None:
    """Lazily initialize all provider singletons."""
    global _providers
    if _providers:
        return

    _providers = {
        "claude": ClaudeProvider(),
        "codex": CodexProvider(),
        "gemini": GeminiProvider(),
        "ollama": OllamaProvider(),
        "lmstudio": OpenAICompatProvider("lmstudio"),
        "localai": OpenAICompatProvider("localai"),
        "vllm": OpenAICompatProvider("vllm"),
        "jan": OpenAICompatProvider("jan"),
    }


def get_provider(provider_id: str) -> ProviderStrategy:
    """Get a provider instance by ID. Defaults to Claude."""
    _init_providers()
    provider = _providers.get(provider_id)
    if provider is None:
        logger.warning(f"Unknown provider '{provider_id}', falling back to Claude")
        provider = _providers["claude"]
    return provider


async def detect_all_providers() -> list[ProviderInfo]:
    """Run detection for all providers concurrently."""
    _init_providers()

    results = await asyncio.gather(
        *[provider.detect() for provider in _providers.values()],
        return_exceptions=True,
    )

    infos: list[ProviderInfo] = []
    for provider_id, result in zip(_providers.keys(), results):
        if isinstance(result, Exception):
            logger.warning(f"Provider detection failed for {provider_id}: {result}")
            continue
        infos.append(result)

    return infos
