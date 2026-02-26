"""
Ollama provider for insights chat.

Uses HTTP streaming to localhost:11434/api/chat (NDJSON format).
"""

import asyncio
import json
import logging
import shutil
import subprocess
from pathlib import Path

from ...websockets.events import broadcast_event
from .base import ProviderInfo, ProviderModel, ProviderStrategy

logger = logging.getLogger(__name__)

DEFAULT_OLLAMA_URL = "http://localhost:11434"

# Keywords that indicate an embedding or non-chat model
EMBEDDING_NAME_KEYWORDS = {"embed", "minilm", "bge", "gte", "e5", "rerank"}
EMBEDDING_FAMILIES = {"bert", "nomic-bert"}


def _is_embedding_model(name: str, details: dict | None = None) -> bool:
    """Check if an Ollama model is an embedding/reranker model (not a chat LLM)."""
    name_lower = name.lower()
    if any(kw in name_lower for kw in EMBEDDING_NAME_KEYWORDS):
        return True
    if details:
        family = details.get("family", "").lower()
        families = {f.lower() for f in details.get("families", [])}
        if family in EMBEDDING_FAMILIES or families & EMBEDDING_FAMILIES:
            return True
    return False


class OllamaProvider(ProviderStrategy):
    """Provider that streams via Ollama HTTP API."""

    def __init__(self, base_url: str = DEFAULT_OLLAMA_URL) -> None:
        self.base_url = base_url

    async def detect(self) -> ProviderInfo:
        info = ProviderInfo(
            provider="ollama",
            available=False,
            display_name="Ollama",
            icon="ollama",
            auth_method=None,
            models=[],
        )

        if not shutil.which("ollama"):
            return info

        # Check if server is running by fetching model list
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                resp.raise_for_status()
                data = resp.json()

                for m in data.get("models", []):
                    name = m["name"]
                    details = m.get("details", {})

                    if _is_embedding_model(name, details):
                        continue

                    info.models.append(ProviderModel(id=name, label=name))

                if info.models:
                    info.available = True
        except Exception as e:
            logger.debug(f"[OllamaProvider] Detection failed: {e}")
            # Fallback: check if ollama is installed but server may be down
            try:
                result = subprocess.run(
                    ["ollama", "list"], capture_output=True, text=True, timeout=5,
                )
                if result.returncode == 0 and result.stdout.strip():
                    lines = result.stdout.strip().splitlines()
                    for line in lines[1:]:
                        parts = line.split()
                        if parts:
                            name = parts[0]
                            if _is_embedding_model(name):
                                continue
                            info.models.append(ProviderModel(id=name, label=name))
                    if info.models:
                        info.available = True
            except Exception:
                pass

        return info

    async def send_message(
        self,
        project_path: Path,
        project_id: str,
        message: str,
        model: str | None,
        model_config: dict | None,
        conversation_history: list[dict] | None,
    ) -> str:
        effective_model = model or (model_config or {}).get("model", "llama3.2:latest")

        # Build messages array with conversation history
        messages = []
        if conversation_history:
            for msg in conversation_history[-10:]:  # Last 10 messages
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", ""),
                })
        messages.append({"role": "user", "content": message})

        payload = {
            "model": effective_model,
            "messages": messages,
            "stream": True,
        }

        logger.info(f"[OllamaProvider] Streaming: {effective_model}")

        try:
            import httpx

            await broadcast_event("insights:chunk", {
                "projectId": project_id,
                "type": "text",
                "content": "",
            })

            accumulated = ""

            async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=10.0)) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/chat",
                    json=payload,
                ) as resp:
                    resp.raise_for_status()

                    async for line in resp.aiter_lines():
                        if not line.strip():
                            continue
                        try:
                            data = json.loads(line)
                            content = data.get("message", {}).get("content", "")
                            if content:
                                accumulated += content
                                await broadcast_event("insights:chunk", {
                                    "projectId": project_id,
                                    "type": "text",
                                    "content": content,
                                })

                            if data.get("done"):
                                break
                        except json.JSONDecodeError:
                            continue

            await broadcast_event("insights:chunk", {
                "projectId": project_id,
                "type": "done",
            })

            return accumulated

        except Exception as e:
            logger.error(f"[OllamaProvider] Error: {e}", exc_info=True)
            await broadcast_event("insights:chunk", {
                "projectId": project_id,
                "type": "error",
                "error": str(e),
            })
            return ""
