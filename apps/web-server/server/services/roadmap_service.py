"""
Roadmap generation service.

Wraps the roadmap_runner.py CLI as an async service with real-time progress streaming.
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


class RoadmapPhase(str, Enum):
    """Roadmap generation phases."""
    STARTING = "starting"
    PROJECT_ANALYSIS = "project_analysis"
    DISCOVERY = "discovery"
    COMPETITOR_ANALYSIS = "competitor_analysis"
    FEATURE_GENERATION = "feature_generation"
    COMPLETE = "complete"
    FAILED = "failed"


# Phase progress percentages
PHASE_PROGRESS = {
    RoadmapPhase.STARTING: 0,
    RoadmapPhase.PROJECT_ANALYSIS: 15,
    RoadmapPhase.DISCOVERY: 40,
    RoadmapPhase.COMPETITOR_ANALYSIS: 60,
    RoadmapPhase.FEATURE_GENERATION: 80,
    RoadmapPhase.COMPLETE: 100,
    RoadmapPhase.FAILED: 0,
}

# Pattern matching for phase detection from stdout
PHASE_PATTERNS = [
    (r"PHASE 1.*PROJECT ANALYSIS", RoadmapPhase.PROJECT_ANALYSIS),
    (r"PHASE 2:.*DISCOVERY", RoadmapPhase.DISCOVERY),
    (r"PHASE 2\.5.*COMPETITOR", RoadmapPhase.COMPETITOR_ANALYSIS),
    (r"PHASE 3.*FEATURE", RoadmapPhase.FEATURE_GENERATION),
    (r"ROADMAP GENERATED", RoadmapPhase.COMPLETE),
]


@dataclass
class RoadmapProgress:
    """Roadmap generation progress information."""
    project_id: str
    phase: RoadmapPhase
    progress: int
    message: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


logger = logging.getLogger(__name__)


class RoadmapService:
    """Service for managing roadmap generation."""

    def __init__(self):
        self.running_tasks: dict[str, asyncio.subprocess.Process] = {}
        self._current_phases: dict[str, RoadmapPhase] = {}

    def is_running(self, project_id: str) -> bool:
        """Check if roadmap generation is running for a project."""
        return project_id in self.running_tasks

    def get_status(self, project_id: str) -> dict:
        """Get the current status for a project's roadmap generation."""
        if project_id not in self.running_tasks:
            return {
                "isRunning": False,
                "status": "idle",
                "progress": 0,
                "message": None,
            }

        phase = self._current_phases.get(project_id, RoadmapPhase.STARTING)
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
        enable_competitor_analysis: bool = False,
        refresh_competitor_analysis: bool = False,
        refresh: bool = False,
    ) -> bool:
        """Start roadmap generation for a project."""
        if self.is_running(project_id):
            logger.warning(f"Roadmap generation already running for project {project_id}")
            return False

        settings = get_settings()
        backend_path = Path(settings.BACKEND_PATH)
        roadmap_runner = backend_path / "runners" / "roadmap_runner.py"

        if not roadmap_runner.exists():
            logger.error(f"roadmap_runner.py not found at {roadmap_runner}")
            await self._emit_error(project_id, "Roadmap runner not found")
            return False

        # Use the web server's Python (which has shared dependencies)
        import os
        import sys
        python_path = sys.executable

        cmd = [
            str(python_path),
            str(roadmap_runner),
            "--project", str(project_path),
        ]

        if enable_competitor_analysis:
            cmd.append("--competitor-analysis")
        if refresh_competitor_analysis:
            cmd.append("--refresh-competitor-analysis")
        if refresh:
            cmd.append("--refresh")

        logger.info(f"Starting roadmap generation for {project_id}: {' '.join(cmd)}")

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
            self._current_phases[project_id] = RoadmapPhase.STARTING

            # Emit initial progress
            await self._emit_progress(project_id, RoadmapPhase.STARTING, "Starting roadmap generation...")

            # Start output processing in background
            asyncio.create_task(self._process_output(project_id, project_path, proc))

            return True

        except Exception as e:
            logger.error(f"Failed to start roadmap generation: {e}")
            await self._emit_error(project_id, str(e))
            return False

    async def stop_generation(self, project_id: str) -> bool:
        """Stop roadmap generation for a project."""
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
                logger.error(f"Error stopping roadmap generation: {e}")

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
        current_phase = RoadmapPhase.STARTING

        try:
            # Process stdout
            async for line_bytes in proc.stdout:
                line = line_bytes.decode("utf-8", errors="replace").rstrip()

                if not line:
                    continue

                logger.debug(f"[Roadmap {project_id}] {line}")

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
                # Success - copy roadmap.json to project root
                await self._finalize_roadmap(project_id, project_path)
                await self._emit_complete(project_id, project_path)
            else:
                # Read stderr for error details
                stderr_output = ""
                if proc.stderr:
                    stderr_bytes = await proc.stderr.read()
                    stderr_output = stderr_bytes.decode("utf-8", errors="replace")

                logger.error(f"Roadmap generation failed with code {return_code}: {stderr_output}")
                await self._emit_error(project_id, f"Generation failed (exit code {return_code})")

        except Exception as e:
            logger.error(f"Error processing roadmap output: {e}")
            await self._emit_error(project_id, str(e))

        finally:
            self._cleanup(project_id)

    def _detect_phase(self, line: str) -> RoadmapPhase | None:
        """Detect phase from output line."""
        for pattern, phase in PHASE_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                return phase
        return None

    async def _finalize_roadmap(self, project_id: str, project_path: Path):
        """Copy roadmap.json from output dir to project .auto-claude directory."""
        roadmap_output = project_path / ".auto-claude" / "roadmap" / "roadmap.json"
        roadmap_dest = project_path / ".auto-claude" / "roadmap.json"

        if roadmap_output.exists():
            try:
                import shutil
                shutil.copy2(roadmap_output, roadmap_dest)
                logger.info(f"Copied roadmap to {roadmap_dest}")
            except Exception as e:
                logger.error(f"Failed to copy roadmap: {e}")

    def _cleanup(self, project_id: str):
        """Clean up after generation completes or fails."""
        self.running_tasks.pop(project_id, None)
        self._current_phases.pop(project_id, None)

    async def _emit_progress(self, project_id: str, phase: RoadmapPhase, message: str):
        """Emit progress event."""
        progress = PHASE_PROGRESS.get(phase, 0)
        logger.info(f"[Roadmap] Emitting progress - projectId: {project_id}, phase: {phase.value}, progress: {progress}%")
        await broadcast_event("roadmap:progress", {
            "projectId": project_id,
            "phase": phase.value,
            "progress": progress,
            "message": message,
        })

    async def _emit_complete(self, project_id: str, project_path: Path):
        """Emit completion event with roadmap data."""
        roadmap_file = project_path / ".auto-claude" / "roadmap.json"
        roadmap_data = None

        if roadmap_file.exists():
            try:
                roadmap_data = json.loads(roadmap_file.read_text())
            except Exception as e:
                logger.error(f"Failed to read roadmap: {e}")

        logger.info(f"[Roadmap] Generation complete - projectId: {project_id}")
        await broadcast_event("roadmap:complete", {
            "projectId": project_id,
            "roadmap": roadmap_data,
        })

    async def _emit_error(self, project_id: str, error: str):
        """Emit error event."""
        logger.error(f"[Roadmap] Error - projectId: {project_id}, error: {error}")
        await broadcast_event("roadmap:error", {
            "projectId": project_id,
            "error": error,
        })

    async def _emit_stopped(self, project_id: str):
        """Emit stopped event."""
        logger.info(f"[Roadmap] Stopped - projectId: {project_id}")
        await broadcast_event("roadmap:stopped", {
            "projectId": project_id,
        })


# Singleton instance
_roadmap_service: RoadmapService | None = None


def get_roadmap_service() -> RoadmapService:
    """Get the singleton roadmap service instance."""
    global _roadmap_service
    if _roadmap_service is None:
        _roadmap_service = RoadmapService()
    return _roadmap_service
