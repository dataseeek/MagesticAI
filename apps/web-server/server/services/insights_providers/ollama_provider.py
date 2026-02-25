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

                embedding_keywords = {"embed", "minilm", "bge", "gte", "e5"}
                embedding_families = {"bert", "nomic-bert"}

                for m in data.get("models", []):
                    name = m["name"]
                    name_lower = name.lower()
                    details = m.get("details", {})
                    families = {f.lower() for f in details.get("families", [])}

                    if families & embedding_families:
                        continue
                    if any(kw in name_lower for kw in embedding_keywords):
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
    ) -> None:
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

        except Exception as e:
            logger.error(f"[OllamaProvider] Error: {e}", exc_info=True)
            await broadcast_event("insights:chunk", {
                "projectId": project_id,
                "type": "error",
                "error": str(e),
            })
