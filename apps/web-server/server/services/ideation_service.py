"""
Ideation generation service.

Wraps the ideation_runner.py CLI as an async service with real-time progress streaming.
"""

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

from ..config import get_settings
from ..websockets.events import broadcast_event


class IdeationPhase(str, Enum):
    """Ideation generation phases."""
    STARTING = "starting"
    ANALYZING = "analyzing"
    GENERATING = "generating"
    COMPLETE = "complete"
    FAILED = "failed"


# Phase progress percentages
PHASE_PROGRESS = {
    IdeationPhase.STARTING: 0,
    IdeationPhase.ANALYZING: 20,
    IdeationPhase.GENERATING: 60,
    IdeationPhase.COMPLETE: 100,
    IdeationPhase.FAILED: 0,
}

# Pattern matching for phase detection from stdout
PHASE_PATTERNS = [
    (r"Analyzing project", IdeationPhase.ANALYZING),
    (r"Generating.*ideas", IdeationPhase.GENERATING),
    (r"IDEATION COMPLETE", IdeationPhase.COMPLETE),
]


@dataclass
class IdeationProgress:
    """Ideation generation progress information."""
    project_id: str
    phase: IdeationPhase
    progress: int
    message: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


logger = logging.getLogger(__name__)


class IdeationService:
    """Service for managing ideation generation."""

    def __init__(self):
        self.running_tasks: dict[str, asyncio.subprocess.Process] = {}
        self._current_phases: dict[str, IdeationPhase] = {}

    def is_running(self, project_id: str) -> bool:
        """Check if ideation generation is running for a project."""
        return project_id in self.running_tasks

    def get_status(self, project_id: str) -> dict:
        """Get the current status for a project's ideation generation."""
        if project_id not in self.running_tasks:
            return {
                "isRunning": False,
                "status": "idle",
                "progress": 0,
                "message": None,
            }

        phase = self._current_phases.get(project_id, IdeationPhase.STARTING)
        return {
            "isRunning": True,
            "status": phase.value,
            "progress": PHASE_PROGRESS.get(phase, 0),
            "message": f"Running: {phase.value.replace('_', ' ').title()}",
        }

    async def start_generation(
        self,
        project_id: str,
        project_path: Path,
        types: list[str],
        context: str | None = None,
        max_ideas: int = 10,
        refresh: bool = False,
    ) -> bool:
        """Start ideation generation for a project."""
        if self.is_running(project_id):
            logger.warning(f"Ideation generation already running for project {project_id}")
            return False

        settings = get_settings()
        backend_path = Path(settings.BACKEND_PATH)
        ideation_runner = backend_path / "runners" / "ideation_runner.py"

        if not ideation_runner.exists():
            logger.error(f"ideation_runner.py not found at {ideation_runner}")
            await self._emit_error(project_id, "Ideation runner not found")
            return False

        # Use the web server's Python (which has shared dependencies)
        import os
        import sys
        python_path = sys.executable

        cmd = [
            str(python_path),
            str(ideation_runner),
            "--project", str(project_path),
            "--max-ideas", str(max_ideas),
        ]

        if types:
            cmd.extend(["--types", ",".join(types)])
        if refresh:
            cmd.append("--refresh")

        logger.info(f"Starting ideation generation for {project_id}: {' '.join(cmd)}")

        # Set up environment with PYTHONPATH pointing to backend
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        # Add backend path to PYTHONPATH so imports work
        existing_pythonpath = env.get("PYTHONPATH", "")
        backend_pythonpath = str(backend_path)
        runners_path = str(backend_path / "runners")
        if existing_pythonpath:
            env["PYTHONPATH"] = f"{backend_pythonpath}:{runners_path}:{existing_pythonpath}"
        else:
            env["PYTHONPATH"] = f"{backend_pythonpath}:{runners_path}"

        try:
            # Start the subprocess - run from backend directory
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(backend_path),
                env=env,
            )

            self.running_tasks[project_id] = proc
            self._current_phases[project_id] = IdeationPhase.STARTING

            # Emit initial progress
            await self._emit_progress(project_id, IdeationPhase.STARTING, "Starting ideation generation...")

            # Start output processing in background
            asyncio.create_task(self._process_output(project_id, project_path, proc))

            return True

        except Exception as e:
            logger.error(f"Failed to start ideation generation: {e}")
            await self._emit_error(project_id, str(e))
            return False

    async def stop_generation(self, project_id: str) -> bool:
        """Stop ideation generation for a project."""
        if not self.is_running(project_id):
            return False

        proc = self.running_tasks.get(project_id)
        if proc:
            try:
                proc.terminate()
                await asyncio.wait_for(proc.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                proc.kill()
            except Exception as e:
                logger.error(f"Error stopping ideation generation: {e}")

        self._cleanup(project_id)
        await self._emit_stopped(project_id)
        return True

    async def _process_output(
        self,
        project_id: str,
        project_path: Path,
        proc: asyncio.subprocess.Process,
    ):
        """Process subprocess output and emit progress events."""
        current_phase = IdeationPhase.STARTING

        try:
            # Process stdout
            async for line_bytes in proc.stdout:
                line = line_bytes.decode("utf-8", errors="replace").rstrip()

                if not line:
                    continue

                logger.debug(f"[Ideation {project_id}] {line}")

                # Check for phase transitions
                new_phase = self._detect_phase(line)
                if new_phase and new_phase != current_phase:
                    current_phase = new_phase
                    self._current_phases[project_id] = current_phase
                    await self._emit_progress(
                        project_id,
                        current_phase,
                        f"Phase: {current_phase.value.replace('_', ' ').title()}"
                    )

            # Wait for process to complete
            return_code = await proc.wait()

            if return_code == 0:
                # Success
                await self._emit_complete(project_id, project_path)
            else:
                # Read stderr for error details
                stderr_output = ""
                if proc.stderr:
                    stderr_bytes = await proc.stderr.read()
                    stderr_output = stderr_bytes.decode("utf-8", errors="replace")

                logger.error(f"Ideation generation failed with code {return_code}: {stderr_output}")
                await self._emit_error(project_id, f"Generation failed (exit code {return_code})")

        except Exception as e:
            logger.error(f"Error processing ideation output: {e}")
            await self._emit_error(project_id, str(e))

        finally:
            self._cleanup(project_id)

    def _detect_phase(self, line: str) -> IdeationPhase | None:
        """Detect phase from output line."""
        for pattern, phase in PHASE_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                return phase
        return None

    def _cleanup(self, project_id: str):
        """Clean up after generation completes or fails."""
        self.running_tasks.pop(project_id, None)
        self._current_phases.pop(project_id, None)

    async def _emit_progress(self, project_id: str, phase: IdeationPhase, message: str):
        """Emit progress event."""
        progress = PHASE_PROGRESS.get(phase, 0)
        logger.info(f"[Ideation] Emitting progress - projectId: {project_id}, phase: {phase.value}, progress: {progress}%")
        await broadcast_event("ideation:progress", {
            "projectId": project_id,
            "phase": phase.value,
            "progress": progress,
            "message": message,
        })

    async def _emit_complete(self, project_id: str, project_path: Path):
        """Emit completion event with ideation data."""
        ideation_file = project_path / ".auto-claude" / "ideation.json"
        ideation_data = None

        if ideation_file.exists():
            try:
                ideation_data = json.loads(ideation_file.read_text())
            except Exception as e:
                logger.error(f"Failed to read ideation: {e}")

        logger.info(f"[Ideation] Generation complete - projectId: {project_id}")
        await broadcast_event("ideation:complete", {
            "projectId": project_id,
            "ideation": ideation_data,
        })

    async def _emit_error(self, project_id: str, error: str):
        """Emit error event."""
        logger.error(f"[Ideation] Error - projectId: {project_id}, error: {error}")
        await broadcast_event("ideation:error", {
            "projectId": project_id,
            "error": error,
        })

    async def _emit_stopped(self, project_id: str):
        """Emit stopped event."""
        logger.info(f"[Ideation] Stopped - projectId: {project_id}")
        await broadcast_event("ideation:stopped", {
            "projectId": project_id,
        })


# Singleton instance
_ideation_service: IdeationService | None = None


def get_ideation_service() -> IdeationService:
    """Get the singleton ideation service instance."""
    global _ideation_service
    if _ideation_service is None:
        _ideation_service = IdeationService()
    return _ideation_service
