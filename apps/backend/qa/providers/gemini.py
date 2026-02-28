"""
GeminiCLIProvider — Adapter wrapping the Gemini CLI
=====================================================

Implements ``BaseLLMProvider`` by spawning the ``gemini`` command-line tool
as a subprocess, sending the QA prompt via stdin, and wrapping the plain-text
response in the message-protocol types expected by ``reviewer.py`` and
``fixer.py``.

Since the Gemini CLI is a text-in / text-out interface it does not natively
support the agentic tool-use loop (file reads, writes, etc.).  The adapter
therefore sends the **complete prompt** (including all context already
embedded by the QA prompt builder) and returns the LLM's text as a single
``AssistantMessage`` containing one ``TextBlock``.  The QA reviewer logic
in ``reviewer.py`` still reads the ``qa_signoff`` status from
``implementation_plan.json``, but it will receive the model's analysis as
pure text with no tool calls in the stream.

Usage::

    from pathlib import Path
    from qa.providers.gemini import GeminiCLIProvider

    provider = GeminiCLIProvider(
        model="gemini-2.0-flash",   # Gemini model (passed via --model)
        gemini_path="gemini",       # executable name / absolute path
        timeout=300,                # subprocess timeout in seconds
        working_dir=project_dir,    # cwd for the subprocess
    )
    async with provider:
        await provider.query(prompt)
        async for msg in provider.receive_response():
            ...

CLI invocation shape::

    gemini [--model <model>] [<extra_args>...]

The prompt is piped via stdin to avoid shell quoting issues with
multi-kilobyte prompt strings.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
from pathlib import Path
from typing import Any, AsyncGenerator, AsyncIterator

from qa.providers import BaseLLMProvider
from qa.providers.types import AssistantMessage, TextBlock

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level defaults (overridable per-instance)
# ---------------------------------------------------------------------------

_DEFAULT_GEMINI_PATH: str = "gemini"
_DEFAULT_MODEL: str = "gemini-2.0-flash"
_DEFAULT_TIMEOUT: int = 300  # seconds


class GeminiCLIProvider(BaseLLMProvider):
    """
    QA LLM provider backed by the Gemini CLI (``gemini`` subprocess).

    The adapter invokes the ``gemini`` executable as a subprocess, pipes the
    QA prompt via *stdin*, waits for the process to finish, then yields the
    captured stdout as a single ``AssistantMessage`` containing one
    ``TextBlock``.

    Because the Gemini CLI does not expose a tool-use protocol, no
    ``ToolUseBlock`` or ``UserMessage`` objects are ever produced.  The QA
    reviewer will receive the model's complete analysis as plain text.

    Args:
        model: Gemini model identifier to request (e.g.
               ``"gemini-2.0-flash"``, ``"gemini-2.5-pro"``).  Passed to
               the CLI via ``--model``.  Set to ``None`` or ``""`` to omit
               the flag and let the CLI use its own default.
        gemini_path: Path or command name for the ``gemini`` executable.
                     Resolved via ``$PATH`` when not an absolute path.
                     Defaults to ``"gemini"``.
        timeout: Maximum number of seconds to wait for the subprocess to
                 complete before raising ``asyncio.TimeoutError``.
                 Defaults to 300 (5 minutes).
        working_dir: Working directory passed to the subprocess via ``cwd``.
                     Defaults to the process's current directory when
                     ``None``.
        extra_args: Additional CLI flags appended after the model flag
                    (e.g. ``["--no-cache"]``).
    """

    def __init__(
        self,
        model: str = _DEFAULT_MODEL,
        gemini_path: str = _DEFAULT_GEMINI_PATH,
        timeout: int = _DEFAULT_TIMEOUT,
        working_dir: Path | None = None,
        extra_args: list[str] | None = None,
    ) -> None:
        self._model = model
        self._gemini_path = gemini_path
        self._timeout = timeout
        self._working_dir = working_dir
        self._extra_args: list[str] = extra_args or []
        self._pending_prompt: str | None = None

        logger.debug(
            "GeminiCLIProvider created",
            extra={
                "model": model,
                "gemini_path": gemini_path,
                "timeout": timeout,
                "working_dir": str(working_dir) if working_dir else None,
            },
        )

    # ------------------------------------------------------------------
    # BaseLLMProvider interface
    # ------------------------------------------------------------------

    async def query(self, prompt: str) -> None:
        """Store the prompt for execution when ``receive_response()`` is called.

        Args:
            prompt: The system + user prompt string assembled by the QA
                    prompt builder (may be several kB of text).
        """
        self._pending_prompt = prompt
        logger.debug(
            "GeminiCLIProvider: prompt stored (length=%d)", len(prompt)
        )

    def receive_response(self) -> AsyncIterator[Any]:
        """Return an async generator that runs the Gemini CLI subprocess.

        The generator invokes ``gemini`` with the stored prompt as stdin,
        captures stdout, and yields a single ``AssistantMessage``.

        Returns:
            An ``AsyncGenerator`` that yields one ``AssistantMessage``
            containing one ``TextBlock`` with the full CLI response.

        Raises:
            RuntimeError: If the ``gemini`` executable cannot be found on
                          ``$PATH``, or if the process exits with a non-zero
                          code *and* produces no stdout.
            asyncio.TimeoutError: If the subprocess exceeds ``self._timeout``
                                  seconds without completing.
        """
        return self._run_gemini()

    async def _run_gemini(self) -> AsyncGenerator[Any, None]:
        """Async generator: invoke the Gemini CLI and yield the response message.

        Yields:
            ``AssistantMessage(content=[TextBlock(text=<response>)])``
        """
        if not self._pending_prompt:
            logger.warning(
                "GeminiCLIProvider.receive_response() called before query() — "
                "no prompt to send"
            )
            return

        # Resolve the executable path early so callers get a clear error
        # message rather than a confusing FileNotFoundError from asyncio.
        resolved_path = shutil.which(self._gemini_path)
        if resolved_path is None:
            raise RuntimeError(
                f"Gemini CLI executable not found: '{self._gemini_path}'. "
                "Install the Gemini CLI or pass the correct path via "
                "gemini_path=... when constructing GeminiCLIProvider."
            )

        cmd = self._build_command()
        cwd = str(self._working_dir) if self._working_dir else None

        logger.debug(
            "GeminiCLIProvider: spawning subprocess cmd=%r cwd=%r", cmd, cwd
        )

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
                f"Gemini CLI subprocess timed out after {self._timeout}s. "
                "Increase timeout= or reduce prompt size."
            )

        stdout_text = stdout_bytes.decode("utf-8", errors="replace").strip()
        stderr_text = stderr_bytes.decode("utf-8", errors="replace").strip()

        logger.debug(
            "GeminiCLIProvider: subprocess finished returncode=%d "
            "stdout_len=%d stderr_len=%d",
            proc.returncode,
            len(stdout_text),
            len(stderr_text),
        )

        # A non-zero exit with no stdout is a fatal error.
        if proc.returncode != 0 and not stdout_text:
            error_detail = stderr_text or f"exit code {proc.returncode}"
            raise RuntimeError(
                f"Gemini CLI exited with an error: {error_detail}"
            )

        # Log stderr as a warning when present but non-fatal.
        if stderr_text:
            logger.warning(
                "Gemini CLI stderr (first 500 chars): %s",
                stderr_text[:500],
            )

        response_text = stdout_text if stdout_text else "(no output from Gemini CLI)"

        yield AssistantMessage(content=[TextBlock(text=response_text)])

    def _build_command(self) -> list[str]:
        """Construct the argv list for the Gemini CLI subprocess.

        The resulting command reads the prompt from *stdin* to avoid shell
        quoting issues with long, multi-line prompt strings.

        Shape::

            gemini [--model <model>] [extra_args...]

        The prompt is supplied via stdin.

        Returns:
            A list of strings suitable for ``asyncio.create_subprocess_exec``.
        """
        cmd: list[str] = [self._gemini_path]

        if self._model:
            cmd += ["--model", self._model]

        if self._extra_args:
            cmd.extend(self._extra_args)

        return cmd

    # ------------------------------------------------------------------
    # Async context manager — no persistent resources to manage
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "GeminiCLIProvider":
        """No-op context entry — the subprocess is spawned per-request."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """No-op context exit — clear pending prompt for hygiene."""
        self._pending_prompt = None


__all__ = ["GeminiCLIProvider"]
