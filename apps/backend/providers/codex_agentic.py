"""
CodexAgenticProvider — Agentic Codex CLI adapter for coding/planning phases
============================================================================

Runs ``codex exec --full-auto`` as a non-interactive subprocess, which handles
file operations and command execution autonomously.  The prompt is sent via
stdin (``-``) and the CLI's output is streamed back as ``AssistantMessage`` /
``TextBlock`` objects.

Unlike ``CodexCLIProvider`` (text-only, ``-q`` flag), this provider uses
``exec --full-auto`` mode which gives Codex full agentic capabilities:
file reads/writes, command execution, etc.  The ``exec`` subcommand runs
headless without requiring a terminal.

Usage::

    from providers.codex_agentic import CodexAgenticProvider

    provider = CodexAgenticProvider(
        model="gpt-5.3-codex",
        working_dir=project_dir,
        timeout=600,
    )
    async with provider:
        await provider.query(prompt)
        async for msg in provider.receive_response():
            ...

CLI invocation shape::

    codex exec --full-auto [--model <model>] [-C <dir>] [<extra_args>...] -
"""

from __future__ import annotations

import asyncio
import logging
import re
import shutil
from pathlib import Path
from typing import Any, AsyncGenerator, AsyncIterator

from providers import BaseLLMProvider
from providers.types import AssistantMessage, TextBlock

logger = logging.getLogger(__name__)

_DEFAULT_CODEX_PATH: str = "codex"
_DEFAULT_MODEL: str = "gpt-5.3-codex"
_DEFAULT_TIMEOUT: int = 600  # 10 minutes for agentic tasks
_MODEL_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._:/-]*$")


class CodexAgenticProvider(BaseLLMProvider):
    """
    Agentic Codex provider for coding/planning/spec/qa_fixer phases.

    Runs ``codex exec --full-auto`` (non-interactive/headless) which handles
    file ops and commands autonomously.  Streams output as
    AssistantMessage/TextBlock messages.

    Args:
        model: Codex model identifier (e.g. ``"gpt-5.3-codex"``).
        codex_path: Path or command name for the ``codex`` executable.
        timeout: Maximum seconds to wait for the subprocess.
        working_dir: Working directory for the subprocess.
        extra_args: Additional CLI flags.
    """

    def __init__(
        self,
        model: str = _DEFAULT_MODEL,
        codex_path: str = _DEFAULT_CODEX_PATH,
        timeout: int = _DEFAULT_TIMEOUT,
        working_dir: Path | None = None,
        extra_args: list[str] | None = None,
    ) -> None:
        if model and not _MODEL_NAME_RE.match(model):
            raise ValueError(
                f"Invalid model name '{model}': must be alphanumeric with . _ : / - separators"
            )
        self._model = model
        self._codex_path = codex_path
        self._timeout = timeout
        self._working_dir = working_dir
        self._extra_args: list[str] = extra_args or []
        for arg in self._extra_args:
            if "\x00" in arg:
                raise ValueError("extra_args must not contain null bytes")
        self._pending_prompt: str | None = None

        logger.debug(
            "CodexAgenticProvider created model=%s working_dir=%s timeout=%d",
            model,
            working_dir,
            timeout,
        )

    async def query(self, prompt: str) -> None:
        """Store the prompt for execution when ``receive_response()`` is called."""
        self._pending_prompt = prompt

    def receive_response(self) -> AsyncIterator[Any]:
        """Return an async generator that runs the Codex CLI in full-auto mode."""
        return self._run_codex()

    async def _run_codex(self) -> AsyncGenerator[Any, None]:
        """Spawn codex --full-auto, stream output as AssistantMessage blocks."""
        if not self._pending_prompt:
            logger.warning("CodexAgenticProvider.receive_response() called before query()")
            return

        resolved_path = shutil.which(self._codex_path)
        if resolved_path is None:
            raise RuntimeError(
                f"Codex CLI executable not found: '{self._codex_path}'. "
                "Install the Codex CLI or pass the correct path."
            )

        cmd = self._build_command()
        cwd = str(self._working_dir) if self._working_dir else None

        logger.debug("CodexAgenticProvider: spawning cmd=%r cwd=%r", cmd, cwd)

        proc: asyncio.subprocess.Process | None = None
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )

            prompt_bytes = self._pending_prompt.encode("utf-8")
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(input=prompt_bytes),
                timeout=float(self._timeout),
            )

        except asyncio.TimeoutError:
            if proc is not None:
                try:
                    proc.kill()
                except ProcessLookupError:
                    pass
            raise asyncio.TimeoutError(
                f"Codex CLI (full-auto) timed out after {self._timeout}s."
            )

        stdout_text = stdout_bytes.decode("utf-8", errors="replace").strip()
        stderr_text = stderr_bytes.decode("utf-8", errors="replace").strip()

        logger.debug(
            "CodexAgenticProvider: finished returncode=%d stdout_len=%d stderr_len=%d",
            proc.returncode,
            len(stdout_text),
            len(stderr_text),
        )

        if proc.returncode != 0 and not stdout_text:
            error_detail = stderr_text or f"exit code {proc.returncode}"
            raise RuntimeError(f"Codex CLI (full-auto) error: {error_detail}")

        if stderr_text:
            logger.warning("Codex CLI stderr (first 500 chars): %s", stderr_text[:500])

        response_text = stdout_text if stdout_text else "(no output from Codex CLI)"

        yield AssistantMessage(content=[TextBlock(text=response_text)])

    def _build_command(self) -> list[str]:
        """Build the argv list for ``codex exec --full-auto``.

        Uses ``exec`` subcommand for non-interactive/headless execution.
        The ``-`` at the end tells Codex to read the prompt from stdin.
        Uses ``-C`` to set the working directory inside the CLI.
        """
        cmd: list[str] = [self._codex_path, "exec", "--full-auto"]

        if self._model:
            cmd += ["--model", self._model]

        if self._working_dir:
            cmd += ["-C", str(self._working_dir)]

        if self._extra_args:
            cmd.extend(self._extra_args)

        # "-" tells codex exec to read prompt from stdin
        cmd.append("-")
        return cmd

    async def __aenter__(self) -> "CodexAgenticProvider":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self._pending_prompt = None


__all__ = ["CodexAgenticProvider"]
