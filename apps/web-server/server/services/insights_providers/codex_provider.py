"""
Codex CLI (OpenAI) provider for insights chat.

Runs `codex --quiet --model <model> "<message>"` as a subprocess.
"""

import asyncio
import logging
import os
import subprocess
from pathlib import Path

from ...websockets.events import broadcast_event
from .base import ProviderInfo, ProviderModel, ProviderStrategy

logger = logging.getLogger(__name__)

# Codex models (static fallback list)
CODEX_MODELS = [
    ProviderModel(id="o4-mini", label="o4-mini"),
    ProviderModel(id="o3", label="o3"),
    ProviderModel(id="gpt-4.1", label="GPT-4.1"),
    ProviderModel(id="gpt-4.1-mini", label="GPT-4.1 Mini"),
]


class CodexProvider(ProviderStrategy):
    """Provider that shells out to the Codex CLI."""

    async def detect(self) -> ProviderInfo:
        # Reuse cli_accounts detection logic
        from ...routes.cli_accounts import _detect_cli_version, _detect_codex_credentials

        version = _detect_cli_version("codex")
        installed = version is not None
        authenticated, auth_method, _ = (False, None, None)

        if installed:
            authenticated, auth_method, _ = _detect_codex_credentials()

        return ProviderInfo(
            provider="codex",
            available=installed and authenticated,
            display_name="Codex (OpenAI)",
            icon="openai",
            auth_method=auth_method,
            models=CODEX_MODELS if installed and authenticated else [],
        )

    async def send_message(
        self,
        project_path: Path,
        project_id: str,
        message: str,
        model: str | None,
        model_config: dict | None,
        conversation_history: list[dict] | None,
    ) -> str:
        cmd = ["bash", "-l", "-c"]

        codex_cmd = "codex --quiet"
        effective_model = model or (model_config or {}).get("model", "o4-mini")
        codex_cmd += f" --model {effective_model}"

        # Build prompt with conversation context for stateless CLI
        full_prompt = message
        if conversation_history:
            context_parts = []
            for msg in conversation_history[-6:]:  # Last 6 messages for context
                role = msg.get("role", "user")
                content = msg.get("content", "")[:500]
                context_parts.append(f"[{role}]: {content}")
            if context_parts:
                full_prompt = "\n".join(context_parts) + f"\n[user]: {message}"

        # Shell-escape the message
        escaped_msg = full_prompt.replace("'", "'\\''")
        codex_cmd += f" '{escaped_msg}'"

        cmd.append(codex_cmd)

        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"

        logger.info(f"[CodexProvider] Starting: codex --quiet --model {effective_model}")

        try:
            await broadcast_event("insights:chunk", {
                "projectId": project_id,
                "type": "text",
                "content": "",
            })

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(project_path),
                env=env,
            )

            accumulated = ""
            async for line_bytes in proc.stdout:
                line = line_bytes.decode("utf-8", errors="replace").rstrip()
                if not line:
                    continue
                accumulated += line + "\n"
                await broadcast_event("insights:chunk", {
                    "projectId": project_id,
                    "type": "text",
                    "content": line + "\n",
                })

            await proc.wait()

            stderr_output = await proc.stderr.read()
            if proc.returncode != 0 and not accumulated.strip():
                stderr_text = stderr_output.decode("utf-8", errors="replace").strip() if stderr_output else ""
                error_msg = stderr_text or f"Codex CLI exited with code {proc.returncode}"
                await broadcast_event("insights:chunk", {
                    "projectId": project_id,
                    "type": "error",
                    "error": error_msg,
                })
                return ""

            await broadcast_event("insights:chunk", {
                "projectId": project_id,
                "type": "done",
            })

            return accumulated

        except Exception as e:
            logger.error(f"[CodexProvider] Error: {e}", exc_info=True)
            await broadcast_event("insights:chunk", {
                "projectId": project_id,
                "type": "error",
                "error": str(e),
            })
            return ""
