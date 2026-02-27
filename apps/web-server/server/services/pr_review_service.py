"""
PR review execution service.

Wraps the GitHub runner's review-pr / followup-review-pr commands as an async
service, enabling PR reviews with real-time progress streaming via WebSocket.

Follows the same subprocess + WebSocket pattern as changelog_service.py.
"""

import asyncio
import json
import logging
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

from ..config import get_settings
from ..websockets.events import broadcast_event


class PRReviewPhase(str, Enum):
    """PR review execution phases."""
    STARTING = "starting"
    FETCHING = "fetching"
    ANALYZING = "analyzing"
    GENERATING = "generating"
    COMPLETE = "complete"
    FAILED = "failed"


# Phase progress percentages
PHASE_PROGRESS = {
    PRReviewPhase.STARTING: 0,
    PRReviewPhase.FETCHING: 15,
    PRReviewPhase.ANALYZING: 40,
    PRReviewPhase.GENERATING: 75,
    PRReviewPhase.COMPLETE: 100,
    PRReviewPhase.FAILED: 0,
}

# Pattern matching for progress detection from runner stdout
# Runner outputs: [PR #N] [XXX%] message
PROGRESS_PATTERN = re.compile(r"\[PR\s*#\d+\]\s*\[\s*(\d+)%\]\s*(.*)")


@dataclass
class PRReviewProgress:
    """PR review progress information."""
    project_id: str
    pr_number: int
    phase: PRReviewPhase
    progress: int
    message: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


logger = logging.getLogger(__name__)


class PRReviewService:
    """Service for managing async PR review execution."""

    def __init__(self):
        self.running_reviews: dict[str, asyncio.subprocess.Process] = {}
        self._current_phases: dict[str, PRReviewPhase] = {}

    def _review_key(self, project_id: str, pr_number: int) -> str:
        """Create a unique key for a project + PR combination."""
        return f"{project_id}:{pr_number}"

    def is_running(self, project_id: str, pr_number: int) -> bool:
        """Check if a review is running for this project + PR."""
        return self._review_key(project_id, pr_number) in self.running_reviews

    def get_status(self, project_id: str, pr_number: int) -> dict:
        """Get the current status for a PR review."""
        key = self._review_key(project_id, pr_number)
        if key not in self.running_reviews:
            return {
                "isRunning": False,
                "status": "idle",
                "progress": 0,
                "message": None,
            }

        phase = self._current_phases.get(key, PRReviewPhase.STARTING)
        return {
            "isRunning": True,
            "status": phase.value,
            "progress": PHASE_PROGRESS.get(phase, 0),
            "message": f"Running: {phase.value.replace('_', ' ').title()}",
        }

    async def start_review(
        self,
        project_id: str,
        pr_number: int,
        project_path: Path,
        followup: bool = False,
    ) -> bool:
        """Start a PR review as an async subprocess.

        Args:
            project_id: The project identifier.
            pr_number: The PR number to review.
            project_path: Filesystem path to the project.
            followup: If True, run a follow-up review instead of initial review.

        Returns:
            True if the review was started, False if already running.
        """
        key = self._review_key(project_id, pr_number)
        if key in self.running_reviews:
            logger.warning(f"PR review already running for {key}")
            return False

        settings = get_settings()
        backend_path = Path(settings.BACKEND_PATH)
        runner_script = backend_path / "runners" / "github" / "runner.py"

        if not runner_script.exists():
            logger.error(f"GitHub runner not found at {runner_script}")
            await self._emit_error(project_id, pr_number, "GitHub runner not found")
            return False

        # Build command
        command = "followup-review-pr" if followup else "review-pr"
        cmd = [
            sys.executable,
            str(runner_script),
            "--project", str(project_path),
            command, str(pr_number),
        ]

        logger.info(f"Starting PR review for {key}: {' '.join(cmd)}")

        # Set up environment
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"

        # Add backend path to PYTHONPATH for imports
        existing_pythonpath = env.get("PYTHONPATH", "")
        backend_pythonpath = str(backend_path)
        github_runner_path = str(backend_path / "runners" / "github")
        if existing_pythonpath:
            env["PYTHONPATH"] = f"{backend_pythonpath}:{github_runner_path}:{existing_pythonpath}"
        else:
            env["PYTHONPATH"] = f"{backend_pythonpath}:{github_runner_path}"

        # Load backend .env for tokens and API keys
        backend_env_file = backend_path / ".env"
        if backend_env_file.exists():
            try:
                with open(backend_env_file) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip().strip('"').strip("'")
                            if k not in env:
                                env[k] = v
            except Exception as e:
                logger.warning(f"Failed to load backend .env: {e}")

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(project_path),
                env=env,
            )

            self.running_reviews[key] = proc
            self._current_phases[key] = PRReviewPhase.STARTING

            # Emit initial progress
            await self._emit_progress(
                project_id, pr_number, PRReviewPhase.STARTING,
                "Starting PR review...",
            )

            # Process output in background
            asyncio.create_task(
                self._process_output(project_id, pr_number, project_path, proc)
            )

            return True

        except Exception as e:
            logger.error(f"Failed to start PR review: {e}")
            await self._emit_error(project_id, pr_number, str(e))
            return False

    async def cancel_review(self, project_id: str, pr_number: int) -> bool:
        """Cancel a running PR review."""
        key = self._review_key(project_id, pr_number)
        if key not in self.running_reviews:
            return False

        proc = self.running_reviews.get(key)
        if proc:
            try:
                proc.terminate()
                await asyncio.wait_for(proc.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                proc.kill()
            except Exception as e:
                logger.error(f"Error cancelling PR review: {e}")

        self._cleanup(key)
        await self._emit_error(project_id, pr_number, "Review cancelled by user")
        return True

    async def _process_output(
        self,
        project_id: str,
        pr_number: int,
        project_path: Path,
        proc: asyncio.subprocess.Process,
    ):
        """Process subprocess output and emit progress events."""
        key = self._review_key(project_id, pr_number)
        stderr_lines: list[str] = []

        try:
            async def read_stderr():
                """Collect stderr for error reporting."""
                async for line_bytes in proc.stderr:
                    line = line_bytes.decode("utf-8", errors="replace").rstrip()
                    if line:
                        stderr_lines.append(line)
                        logger.debug(f"[{key}] STDERR: {line}")

            # Start stderr reader in background
            stderr_task = asyncio.create_task(read_stderr())

            # Read stdout line by line
            async for line_bytes in proc.stdout:
                line = line_bytes.decode("utf-8", errors="replace").rstrip()
                if not line:
                    continue
                logger.debug(f"[{key}] {line}")

                # Parse progress from runner output
                phase, progress, message = self._parse_progress(line)
                if phase:
                    self._current_phases[key] = phase
                    await self._emit_progress(
                        project_id, pr_number, phase, message, progress,
                    )

            # Wait for stderr reader to finish
            await stderr_task

            # Wait for process completion
            return_code = await proc.wait()

            if return_code == 0:
                await self._emit_complete(project_id, pr_number, project_path)
            else:
                error_msg = (
                    "\n".join(stderr_lines[-5:])
                    if stderr_lines
                    else f"PR review failed with exit code {return_code}"
                )
                logger.error(f"PR review failed for {key}: {error_msg}")
                await self._emit_error(project_id, pr_number, error_msg)

        except asyncio.CancelledError:
            logger.info(f"PR review cancelled for {key}")
            raise
        except Exception as e:
            logger.error(f"Error processing PR review output: {e}", exc_info=True)
            await self._emit_error(project_id, pr_number, f"Unexpected error: {str(e)}")
        finally:
            self._cleanup(key)

    def _parse_progress(self, line: str) -> tuple[PRReviewPhase | None, int, str]:
        """Parse a runner stdout line into phase, progress percentage, and message.

        Runner outputs lines like: [PR #123] [ 25%] Fetching PR data...
        """
        match = PROGRESS_PATTERN.match(line)
        if not match:
            return None, 0, ""

        progress = int(match.group(1))
        message = match.group(2).strip()

        # Map progress percentage ranges to phases
        if progress <= 10:
            phase = PRReviewPhase.FETCHING
        elif progress <= 50:
            phase = PRReviewPhase.ANALYZING
        elif progress < 100:
            phase = PRReviewPhase.GENERATING
        else:
            phase = PRReviewPhase.COMPLETE

        return phase, progress, message

    async def _emit_progress(
        self,
        project_id: str,
        pr_number: int,
        phase: PRReviewPhase,
        message: str,
        progress: int | None = None,
    ):
        """Emit progress event via WebSocket."""
        if progress is None:
            progress = PHASE_PROGRESS.get(phase, 0)

        logger.info(f"[{project_id}:PR#{pr_number}] Phase: {phase.value} ({progress}%) - {message}")

        await broadcast_event("pr:review-progress", {
            "projectId": project_id,
            "phase": phase.value,
            "prNumber": pr_number,
            "progress": progress,
            "message": message,
        })

    async def _emit_complete(
        self,
        project_id: str,
        pr_number: int,
        project_path: Path,
    ):
        """Emit completion event via WebSocket.

        Reads stored review result from disk if available.
        """
        logger.info(f"[{project_id}:PR#{pr_number}] Review complete")

        # Try to read stored review result JSON from the project's .magestic-ai directory
        # Runner saves to: .magestic-ai/github/pr/review_{pr_number}.json
        result_data = None
        review_file = (
            project_path / ".magestic-ai" / "github" / "pr" / f"review_{pr_number}.json"
        )
        if review_file.exists():
            try:
                result_data = json.loads(review_file.read_text())
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Failed to read review result: {e}")

        await broadcast_event("pr:review-complete", {
            "projectId": project_id,
            "prNumber": pr_number,
            "result": result_data,
        })

    async def _emit_error(
        self,
        project_id: str,
        pr_number: int,
        error: str,
    ):
        """Emit error event via WebSocket."""
        logger.error(f"[{project_id}:PR#{pr_number}] Review error: {error}")

        await broadcast_event("pr:review-error", {
            "projectId": project_id,
            "prNumber": pr_number,
            "error": error,
        })

    def _cleanup(self, key: str):
        """Clean up tracking state for a review."""
        self.running_reviews.pop(key, None)
        self._current_phases.pop(key, None)


# Singleton instance
_pr_review_service: PRReviewService | None = None


def get_pr_review_service() -> PRReviewService:
    """Get the singleton PRReviewService instance."""
    global _pr_review_service
    if _pr_review_service is None:
        _pr_review_service = PRReviewService()
    return _pr_review_service
