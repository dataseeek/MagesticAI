"""
Agent execution service.

Wraps the existing run.py and spec_runner.py CLI tools as async services,
enabling task execution with real-time streaming of logs and progress.
"""

import asyncio
import json
import os
import re
import shutil
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

from ..config import get_settings
from ..websockets.events import emit_task_status, emit_task_update, emit_task_logs_stream, emit_subtask_update


class TaskPhase(str, Enum):
    """Task execution phases."""

    SPEC_CREATION = "spec_creation"
    PLANNING = "planning"
    PLAN_REVIEW = "plan_review"  # Paused for human plan approval
    CODING = "coding"
    QA_REVIEW = "qa_review"
    QA_FIXING = "qa_fixing"
    COMPLETED = "completed"
    FAILED = "failed"


def phase_to_status(phase: TaskPhase) -> str:
    """Map execution phase to task status for kanban column placement."""
    mapping = {
        TaskPhase.SPEC_CREATION: "in_progress",
        TaskPhase.PLANNING: "in_progress",
        TaskPhase.PLAN_REVIEW: "human_review",  # Paused for human plan approval
        TaskPhase.CODING: "in_progress",
        TaskPhase.QA_REVIEW: "ai_review",
        TaskPhase.QA_FIXING: "in_progress",
        TaskPhase.COMPLETED: "human_review",
        TaskPhase.FAILED: "human_review",
    }
    return mapping.get(phase, "in_progress")


def phase_to_review_reason(phase: TaskPhase) -> str | None:
    """Map execution phase to reviewReason field value.

    Returns the appropriate reviewReason for phases that result in human_review status:
    - PLAN_REVIEW: "plan_review" (waiting for plan approval before coding)
    - COMPLETED: "completed" (task finished successfully, needs final approval)
    - FAILED: "errors" (task failed, needs human intervention)

    Returns None for phases that don't require a reviewReason.
    """
    mapping = {
        TaskPhase.PLAN_REVIEW: "plan_review",
        TaskPhase.COMPLETED: "completed",
        TaskPhase.FAILED: "errors",
    }
    return mapping.get(phase)


# Phase ranges for overall progress scaling (start%, end%)
# Maps within-phase progress (0-100) to an overall range so progress is monotonically increasing.
PHASE_RANGES: dict[str, tuple[float, float]] = {
    "spec_creation": (0, 20),
    "planning": (0, 20),
    "plan_review": (20, 20),   # Fixed at 20%
    "coding": (20, 80),
    "qa_review": (80, 95),
    "qa_fixing": (80, 95),
    "completed": (95, 100),
    "failed": (0, 0),          # Keep whatever was last
}


def scale_progress(phase: str, phase_progress: float) -> float:
    """Scale within-phase progress (0-100) to overall progress range.

    Example: coding phase at 50% → 20 + (50/100) × 60 = 50% overall.
    """
    start, end = PHASE_RANGES.get(phase, (0, 100))
    width = end - start
    return round(start + (phase_progress / 100) * width)


@dataclass
class TaskProgress:
    """Real-time task progress information."""

    task_id: str
    phase: TaskPhase
    message: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    subtask: str | None = None
    subtask_index: int | None = None
    subtask_total: int | None = None
    percentage: float | None = None
    overall_progress: float | None = None  # Override scaled overall progress
    sequence_number: int = 0  # For frontend out-of-order detection
    started_at: str | None = None  # Task start time for UI display
    data: dict = field(default_factory=dict)


@dataclass
class TaskLog:
    """A single log entry from task execution."""

    task_id: str
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    level: str = "info"  # info, warning, error, debug
    source: str = "agent"  # agent, stdout, stderr


class TaskLogWriter:
    """Writes detailed phase logs to task_logs.json."""

    # Tool patterns for Claude Code CLI output
    TOOL_PATTERNS = [
        # Pattern: "⏺ ToolName" or emoji + tool name
        (r'[⏺🔧📖✏️📝🔍💻]\s*(Read|Write|Edit|Bash|Glob|Grep|Task|WebFetch|WebSearch|LSP|NotebookEdit)\b', 'tool_start'),
        # Pattern: "Tool: ToolName" format
        (r'^Tool:\s*(Read|Write|Edit|Bash|Glob|Grep|Task|WebFetch|WebSearch|LSP|NotebookEdit)\b', 'tool_start'),
        # Pattern: Claude Code verbose format "Using Read tool"
        (r'Using\s+(Read|Write|Edit|Bash|Glob|Grep|Task|WebFetch|WebSearch|LSP|NotebookEdit)\s+tool', 'tool_start'),
        # Pattern: Tool invocation with parameters like "Read(file_path=...)"
        (r'^(Read|Write|Edit|Bash|Glob|Grep|Task|WebFetch|WebSearch|LSP|NotebookEdit)\s*\(', 'tool_start'),
    ]

    # Phase mapping from TaskPhase to task_logs.json phases
    # Note: COMPLETED and FAILED are NOT mapped here - they represent task
    # completion states, not execution phases. Use _get_current_phase() to
    # determine which phase the task was actually in when it completed/failed.
    PHASE_MAP = {
        TaskPhase.SPEC_CREATION: "planning",
        TaskPhase.PLANNING: "planning",
        TaskPhase.CODING: "coding",
        TaskPhase.QA_REVIEW: "validation",
        TaskPhase.QA_FIXING: "validation",
    }

    def __init__(self, spec_dir: Path):
        self.spec_dir = spec_dir
        self.log_file = spec_dir / "task_logs.json"
        self._current_tool: str | None = None
        self._tool_start_time: str | None = None
        self._tool_input: str | None = None
        self._pending_tool_output: list[str] = []
        self._initialized = False
        # Throttling for text emission (avoid flooding WebSocket)
        self._last_text_emit_time: float = 0
        self._text_emit_interval: float = 1.0  # seconds
        self._pending_text_lines: list[str] = []

    def _ensure_initialized(self, spec_id: str) -> dict:
        """Ensure task_logs.json exists with proper structure."""
        if self.log_file.exists():
            try:
                with open(self.log_file) as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError):
                pass

        # Create new structure
        now = datetime.now().isoformat()
        return {
            "spec_id": spec_id,
            "created_at": now,
            "updated_at": now,
            "phases": {
                "planning": {
                    "phase": "planning",
                    "status": "pending",
                    "started_at": None,
                    "completed_at": None,
                    "entries": []
                },
                "coding": {
                    "phase": "coding",
                    "status": "pending",
                    "started_at": None,
                    "completed_at": None,
                    "entries": []
                },
                "validation": {
                    "phase": "validation",
                    "status": "pending",
                    "started_at": None,
                    "completed_at": None,
                    "entries": []
                }
            }
        }

    def _save(self, data: dict) -> None:
        """Save task_logs.json."""
        self.spec_dir.mkdir(parents=True, exist_ok=True)
        data["updated_at"] = datetime.now().isoformat()
        with open(self.log_file, 'w') as f:
            json.dump(data, f, indent=2)

    def _detect_tool(self, line: str) -> tuple[str, str] | None:
        """Detect tool invocation in a line. Returns (tool_name, tool_input) or None."""
        for pattern, _ in self.TOOL_PATTERNS:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                tool_name = match.group(1)
                # Try to extract input after tool name
                input_match = re.search(rf'{tool_name}\s*\(([^)]*)\)', line)
                tool_input = input_match.group(1) if input_match else ""
                # Also check for file paths or other context
                if not tool_input:
                    path_match = re.search(r'["\']([^"\']+)["\']', line)
                    if path_match:
                        tool_input = path_match.group(1)
                return (tool_name, tool_input[:200] if tool_input else "")
        return None

    def _maybe_emit_text(self, spec_id: str, phase: TaskPhase) -> None:
        """Emit accumulated text if enough time has passed (throttled)."""
        import time
        now = time.time()
        if now - self._last_text_emit_time >= self._text_emit_interval:
            self._flush_pending_text(spec_id, phase)

    def _flush_pending_text(self, spec_id: str, phase: TaskPhase) -> None:
        """Flush accumulated text lines as a single entry."""
        import time
        if self._pending_text_lines:
            # Take last 20 lines to avoid huge entries
            content = "\n".join(self._pending_text_lines[-20:])
            self.add_entry(spec_id, phase, "text", content)
            self._pending_text_lines = []
            self._last_text_emit_time = time.time()

    def add_entry(self, spec_id: str, phase: TaskPhase, entry_type: str,
                  content: str, tool_name: str | None = None,
                  tool_input: str | None = None, detail: str | None = None,
                  subphase: str | None = None) -> None:
        """Add a log entry to the appropriate phase."""
        data = self._ensure_initialized(spec_id)
        phase_key = self.PHASE_MAP.get(phase, "coding")

        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": entry_type,
            "content": content,
        }

        if tool_name:
            entry["tool_name"] = tool_name
        if tool_input:
            entry["tool_input"] = tool_input
        if detail:
            entry["detail"] = detail[:5000]  # Limit detail size
        if subphase:
            entry["subphase"] = subphase

        data["phases"][phase_key]["entries"].append(entry)

        # Update phase status
        if data["phases"][phase_key]["status"] == "pending":
            data["phases"][phase_key]["status"] = "active"
            data["phases"][phase_key]["started_at"] = datetime.now().isoformat()

        self._save(data)

        # Emit WebSocket event for real-time streaming to open task detail modals
        # Format as TaskLogStreamChunk to match frontend interface
        stream_chunk = {
            "type": entry_type,
            "content": content,
            "phase": phase_key,
            "timestamp": entry["timestamp"],
        }
        # Add tool info if present
        if tool_name:
            stream_chunk["tool"] = {"name": tool_name}
            if tool_input:
                stream_chunk["tool"]["input"] = tool_input
        # Add subtask info if present (from subphase)
        if subphase:
            stream_chunk["subtask_id"] = subphase

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(emit_task_logs_stream(spec_id, stream_chunk))
        except RuntimeError:
            # No event loop running, skip WebSocket emit
            pass

    def process_line(self, spec_id: str, phase: TaskPhase, line: str) -> None:
        """Process a line of output and detect tool usage."""
        if not line.strip():
            return

        # Check for tool invocation
        tool_info = self._detect_tool(line)

        if tool_info:
            # Flush pending text before starting a new tool
            self._flush_pending_text(spec_id, phase)

            # If there was a previous tool, close it
            if self._current_tool:
                self.add_entry(
                    spec_id, phase, "tool_end",
                    f"Completed {self._current_tool}",
                    tool_name=self._current_tool,
                    detail="\n".join(self._pending_tool_output[-50:]) if self._pending_tool_output else None
                )

            # Start new tool
            tool_name, tool_input = tool_info
            self._current_tool = tool_name
            self._tool_start_time = datetime.now().isoformat()
            self._tool_input = tool_input
            self._pending_tool_output = []

            self.add_entry(
                spec_id, phase, "tool_start",
                f"Using {tool_name}",
                tool_name=tool_name,
                tool_input=tool_input
            )
        elif self._current_tool:
            # Accumulate output for current tool
            self._pending_tool_output.append(line)

            # Check for tool completion patterns
            if any(p in line.lower() for p in ['done', 'completed', 'success', 'error', 'failed']):
                # Might be end of tool, but don't close yet - let next tool close it
                pass
        else:
            # Not in a tool context - accumulate text and emit periodically
            self._pending_text_lines.append(line)
            self._maybe_emit_text(spec_id, phase)

    def set_phase_status(self, spec_id: str, phase: TaskPhase, status: str) -> None:
        """Update phase status (active, completed, failed)."""
        data = self._ensure_initialized(spec_id)
        phase_key = self.PHASE_MAP.get(phase, "coding")

        data["phases"][phase_key]["status"] = status

        if status == "active" and not data["phases"][phase_key]["started_at"]:
            data["phases"][phase_key]["started_at"] = datetime.now().isoformat()
        elif status in ("completed", "failed"):
            data["phases"][phase_key]["completed_at"] = datetime.now().isoformat()

            # Flush any pending text
            self._flush_pending_text(spec_id, phase)

            # Close any pending tool
            if self._current_tool:
                self.add_entry(
                    spec_id, phase, "tool_end",
                    f"Completed {self._current_tool}",
                    tool_name=self._current_tool,
                    detail="\n".join(self._pending_tool_output[-50:]) if self._pending_tool_output else None
                )
                self._current_tool = None
                self._pending_tool_output = []

        self._save(data)

    def finalize(self, spec_id: str, phase: TaskPhase) -> None:
        """Finalize logging - close any pending tools and flush text."""
        # Flush any pending text first
        self._flush_pending_text(spec_id, phase)

        if self._current_tool:
            self.add_entry(
                spec_id, phase, "tool_end",
                f"Completed {self._current_tool}",
                tool_name=self._current_tool,
                detail="\n".join(self._pending_tool_output[-50:]) if self._pending_tool_output else None
            )
            self._current_tool = None
            self._pending_tool_output = []


class AgentService:
    """Service for executing AI agents on tasks."""

    def __init__(self):
        self.settings = get_settings()
        self.running_tasks: dict[str, asyncio.subprocess.Process] = {}
        self._log_callbacks: dict[str, list[Callable]] = {}
        self._progress_callbacks: dict[str, list[Callable]] = {}
        self._task_log_writers: dict[str, tuple[TaskLogWriter, TaskLogWriter]] = {}
        # Track sequence numbers per task for frontend out-of-order detection
        self._task_sequence_numbers: dict[str, int] = {}
        # Track task start times for UI display
        self._task_start_times: dict[str, str] = {}
        # Track user IDs per task for email notifications
        self._task_user_ids: dict[str, str] = {}
        # Track current execution phase per task (for proper phase status on completion)
        self._task_current_phases: dict[str, TaskPhase] = {}
        # Track which Claude profile each task is using (for reactive failover)
        self._task_profiles: dict[str, dict] = {}
        # Track rate limit detection per task to allow reactive failover
        self._task_rate_limits: dict[str, bool] = {}
        # Track previous subtask statuses per task for granular change detection
        # Format: {task_id: {subtask_id: status_string}}
        self._task_subtask_states: dict[str, dict[str, str]] = {}
        # Track spec directory per task for reading implementation plans
        self._spec_dirs: dict[str, Path] = {}

    @property
    def backend_path(self) -> Path:
        """Get path to the backend directory."""
        return Path(self.settings.BACKEND_PATH)

    def register_log_callback(self, task_id: str, callback: Callable) -> Callable:
        """Register a callback for task logs. Returns unregister function."""
        if task_id not in self._log_callbacks:
            self._log_callbacks[task_id] = []
        self._log_callbacks[task_id].append(callback)
        return lambda: self._log_callbacks.get(task_id, []).remove(callback)

    def register_progress_callback(self, task_id: str, callback: Callable) -> Callable:
        """Register a callback for task progress. Returns unregister function."""
        if task_id not in self._progress_callbacks:
            self._progress_callbacks[task_id] = []
        self._progress_callbacks[task_id].append(callback)
        return lambda: self._progress_callbacks.get(task_id, []).remove(callback)

    async def _emit_log(self, log: TaskLog) -> None:
        """Emit a log to all registered callbacks."""
        callbacks = self._log_callbacks.get(log.task_id, [])
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(log)
                else:
                    callback(log)
            except Exception:
                pass

    def _get_next_sequence_number(self, task_id: str) -> int:
        """Get the next sequence number for a task (for out-of-order detection)."""
        current = self._task_sequence_numbers.get(task_id, 0)
        next_seq = current + 1
        self._task_sequence_numbers[task_id] = next_seq
        return next_seq

    def _get_current_phase(self, task_id: str) -> TaskPhase:
        """Get the current execution phase for a task.

        Returns the tracked phase or defaults to PLANNING if unknown.
        This is used to determine which phase to mark as completed/failed
        when a task finishes, avoiding incorrect status on phases that were
        never actually reached.
        """
        return self._task_current_phases.get(task_id, TaskPhase.PLANNING)

    def _resolve_claude_token(self, exclude_profile_id: str | None = None) -> tuple[str | None, str | None, str | None]:
        """Resolve Claude OAuth token from profiles with fallback chain.

        Resolution order:
        1. Environment override (CLAUDE_CODE_OAUTH_TOKEN already set)
        2. Active profile from ~/.magestic-ai/claude-profiles.json
        3. Best available profile (excluding failed profile if provided)
        4. Fallback to ~/.claude/oauth_token

        Args:
            exclude_profile_id: Profile ID to exclude (for retry after failure)

        Returns:
            Tuple of (token, profile_id, profile_name) or (None, None, None) if no token found
        """
        import logging
        logger = logging.getLogger(__name__)

        # Check environment override first
        if "CLAUDE_CODE_OAUTH_TOKEN" in os.environ:
            # Allow failover when this "env-override" profile is excluded.
            if exclude_profile_id != "env-override":
                logger.info("[AgentService] Using CLAUDE_CODE_OAUTH_TOKEN from environment")
                return (os.environ["CLAUDE_CODE_OAUTH_TOKEN"], "env-override", "Environment Override")
            logger.info("[AgentService] Skipping environment token due to exclude_profile_id=env-override (failover enabled)")

        # Load claude-profiles.json
        profiles_file = Path(self.settings.PROJECTS_DATA_DIR) / "claude-profiles.json"
        from ..paths import get_data_file
        legacy_profiles_file = get_data_file("claude-profiles.json")
        if not profiles_file.exists() and legacy_profiles_file.exists():
            profiles_file = legacy_profiles_file
            logger.debug(f"[AgentService] Using legacy profiles file at {profiles_file}")

        if profiles_file.exists():
            try:
                data = json.loads(profiles_file.read_text())
                profiles = data.get("profiles", [])
                active_id = data.get("activeProfileId")

                # Filter usable profiles (has token, not excluded)
                usable = [
                    p for p in profiles
                    if p.get("id") != exclude_profile_id
                    and (p.get("oauthToken") or p.get("token"))  # Support both field names
                ]

                if usable:
                    # Prefer active profile if it's usable
                    for p in usable:
                        if p.get("id") == active_id:
                            token = p.get("oauthToken") or p.get("token")
                            profile_id = p.get("id")
                            profile_name = p.get("name", "Active Profile")
                            logger.info(f"[AgentService] Using active profile: {profile_name} ({profile_id})")
                            return (token, profile_id, profile_name)

                    # Use first usable profile
                    p = usable[0]
                    token = p.get("oauthToken") or p.get("token")
                    profile_id = p.get("id")
                    profile_name = p.get("name", "Default Profile")
                    logger.info(f"[AgentService] Using profile: {profile_name} ({profile_id})")
                    return (token, profile_id, profile_name)

            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"[AgentService] Failed to load claude-profiles.json: {e}")

        # Fallback to static token file
        token_file = Path.home() / ".claude" / "oauth_token"
        if token_file.exists():
            token = token_file.read_text().strip()
            logger.info("[AgentService] Using fallback token from ~/.claude/oauth_token")
            return (token, "static-fallback", "Static Token")

        logger.warning("[AgentService] No Claude token found")
        return (None, None, None)

    def _is_early_failure(self, spec_dir: Path, exit_code: int) -> bool:
        """Check if task failure is an early failure (no logs written).

        Early failure criteria:
        - Exit code is non-zero
        - task_logs.json either doesn't exist OR has no entries in any phase

        This indicates the agent failed immediately without making progress,
        typically due to auth/rate-limit issues.

        Args:
            spec_dir: Path to the spec directory containing task_logs.json
            exit_code: Process exit code

        Returns:
            True if this is an early failure eligible for retry
        """
        if exit_code == 0:
            return False

        task_logs_file = spec_dir / "task_logs.json"

        # If file doesn't exist, it's an early failure
        if not task_logs_file.exists():
            return True

        try:
            data = json.loads(task_logs_file.read_text())
            phases = data.get("phases", {})

            # Check if any phase has entries
            for phase_name, phase_data in phases.items():
                entries = phase_data.get("entries", [])
                if entries:
                    # Found entries - this is NOT an early failure
                    return False

            # No entries in any phase - early failure
            return True

        except (json.JSONDecodeError, OSError):
            # Can't read logs - assume early failure to be safe
            return True

    def _should_retry_with_failover(self) -> bool:
        """Check if auto-switch settings allow profile failover.

        Checks:
        - enabled: Master switch for auto-switching
        - autoSwitchOnRateLimit: Reactive recovery toggle

        Returns:
            True if both settings are enabled
        """
        import logging
        logger = logging.getLogger(__name__)

        # Primary path: ~/.magestic-ai/auto-switch.json
        settings_file = Path(self.settings.PROJECTS_DATA_DIR) / "auto-switch.json"

        if not settings_file.exists():
            logger.debug(f"[AgentService] Auto-switch settings not found at {settings_file}, failover disabled")
            return False

        try:
            data = json.loads(settings_file.read_text())
            enabled = data.get("enabled", False)
            auto_switch_on_rate_limit = data.get("autoSwitchOnRateLimit", False)

            if enabled and auto_switch_on_rate_limit:
                logger.info("[AgentService] Auto-switch enabled - failover allowed")
                return True
            else:
                logger.debug(f"[AgentService] Auto-switch disabled - enabled: {enabled}, autoSwitchOnRateLimit: {auto_switch_on_rate_limit}")
                return False

        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"[AgentService] Failed to read auto-switch settings: {e}")
            return False

    def _is_rate_limit_line(self, line: str) -> bool:
        """Detect rate limit messages in agent output."""
        text = line.lower()
        patterns = [
            "you've hit your limit",
            "you’ve hit your limit",  # curly apostrophe
            "youve hit your limit",
        ]
        return any(p in text for p in patterns)

    async def _emit_profile_switch(
        self,
        task_id: str,
        old_profile_id: str,
        new_profile_id: str,
        new_profile_name: str,
        reason: str
    ) -> None:
        """Emit profile switch event via WebSocket.

        Args:
            task_id: Task identifier
            old_profile_id: Previous profile ID that failed
            new_profile_id: New profile ID being used
            new_profile_name: New profile display name
            reason: Reason for switch (e.g., "early_failure")
        """
        from ..websockets.events import broadcast_event

        await broadcast_event("task:profile-switch", {
            "taskId": task_id,
            "oldProfileId": old_profile_id,
            "newProfileId": new_profile_id,
            "newProfileName": new_profile_name,
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        })

    def _update_active_profile(self, profile_id: str, profile_name: str, reason: str = "rate_limit") -> None:
        """Update active profile system-wide when reactive failover occurs.

        This updates the activeProfileId in claude-profiles.json so that all future
        tasks automatically use the new profile instead of repeatedly failing.

        Args:
            profile_id: ID of new profile to make active
            profile_name: Name for logging
            reason: Why the switch occurred (e.g., "rate_limit", "reactive_failover")
        """
        import logging
        logger = logging.getLogger(__name__)

        profiles_file = Path(self.settings.PROJECTS_DATA_DIR) / "claude-profiles.json"
        from ..paths import get_data_file
        legacy_profiles_file = get_data_file("claude-profiles.json")

        if not profiles_file.exists() and legacy_profiles_file.exists():
            profiles_file = legacy_profiles_file
            logger.debug(f"[AgentService] Using legacy profiles file at {profiles_file}")

        if not profiles_file.exists():
            logger.warning("[AgentService] claude-profiles.json not found, skipping active profile update")
            return

        try:
            # Read current profiles
            data = json.loads(profiles_file.read_text())
            old_active = data.get("activeProfileId")

            # Update active profile
            data["activeProfileId"] = profile_id

            # Write back with secure permissions
            profiles_file.write_text(json.dumps(data, indent=2))
            profiles_file.chmod(0o600)

            # Update env token to match active profile (if available)
            token = None
            for profile in data.get("profiles", []):
                if profile.get("id") == profile_id:
                    token = profile.get("oauthToken") or profile.get("token")
                    break

            if token:
                os.environ["CLAUDE_CODE_OAUTH_TOKEN"] = token
                logger.info("[AgentService] Updated CLAUDE_CODE_OAUTH_TOKEN for active profile")
            else:
                logger.warning("[AgentService] Active profile has no token; env not updated")

            logger.info(f"[AgentService] Updated active profile: {old_active} → {profile_id} (reason: {reason})")

            # Emit WebSocket event for system-wide profile change
            from ..websockets.events import broadcast_event
            asyncio.create_task(broadcast_event("profile:changed", {
                "oldProfileId": old_active,
                "newProfileId": profile_id,
                "newProfileName": profile_name,
                "reason": reason,
                "timestamp": datetime.now().isoformat()
            }))

        except Exception as e:
            logger.error(f"[AgentService] Failed to update active profile: {e}")

    async def _retry_task_with_profile(
        self,
        task_id: str,
        project_path: Path,
        spec_id: str,
        cmd: list[str],
        env: dict,
        failed_profile_id: str,
        reason: str,
    ) -> asyncio.subprocess.Process | None:
        """Retry task execution with a different Claude profile.

        Args:
            task_id: Task identifier
            project_path: Project directory
            spec_id: Spec identifier
            cmd: Command to execute (same as original)
            env: Environment dict (will update token)
            failed_profile_id: Profile ID that failed (to exclude)

        Returns:
            New subprocess or None if retry not possible
        """
        import logging
        logger = logging.getLogger(__name__)

        # Resolve alternate token (excluding failed profile)
        token, profile_id, profile_name = self._resolve_claude_token(exclude_profile_id=failed_profile_id)

        if not token:
            logger.warning(f"[AgentService] No alternate profile available for retry (excluded: {failed_profile_id})")
            return None

        if profile_id == failed_profile_id:
            logger.warning(f"[AgentService] Only profile available is the one that failed ({failed_profile_id})")
            return None

        # Update environment with new token
        env["CLAUDE_CODE_OAUTH_TOKEN"] = token

        # Log profile switch
        logger.info(f"[AgentService] Retrying with profile: {profile_name} ({profile_id})")

        # Emit WebSocket event for profile switch
        await self._emit_profile_switch(
            task_id=task_id,
            old_profile_id=failed_profile_id,
            new_profile_id=profile_id,
            new_profile_name=profile_name,
            reason=reason,
        )

        # Update active profile system-wide (only for rate limit, not early failure)
        if reason == "rate_limit":
            self._update_active_profile(profile_id, profile_name, reason="reactive_failover")

        # Update tracking
        if task_id in self._task_profiles:
            self._task_profiles[task_id] = {
                "profileId": profile_id,
                "profileName": profile_name,
                "attempt": 2,  # Second attempt
                "previousProfileId": failed_profile_id
            }

        # Relaunch subprocess with new token
        import pty
        master_fd, slave_fd = pty.openpty()

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=slave_fd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(project_path),
            env=env,
        )

        os.close(slave_fd)

        return proc

    async def _emit_progress(self, progress: TaskProgress, previous_phase: TaskPhase | None = None) -> None:
        """Emit progress to all registered callbacks and broadcast via WebSocket.

        If previous_phase is provided and differs from current phase, also emits
        a status change event to update the kanban board column.
        """
        # Broadcast via WebSocket for real-time frontend updates
        try:
            # Use task:update event which frontend handles correctly for progress
            # Frontend's onTaskUpdate handler expects: {taskId, executionProgress?, phase?, subtasks?, ...}
            phase_progress = progress.percentage or 0
            phase_value = progress.phase.value if progress.phase else "coding"
            # Scale within-phase progress to overall range, unless explicitly overridden
            if progress.overall_progress is not None:
                overall_progress = progress.overall_progress
            else:
                overall_progress = scale_progress(phase_value, phase_progress)

            # Get sequence number for out-of-order detection
            sequence_number = self._get_next_sequence_number(progress.task_id)

            # Get task start time (tracked when task started)
            started_at = self._task_start_times.get(progress.task_id)

            # Read subtasks from implementation_plan.json for real-time UI updates
            # Frontend needs the full subtasks array to display checkboxes and status
            subtasks_data = []
            try:
                # Get spec directory from task metadata
                spec_dir = self._spec_dirs.get(progress.task_id)
                if spec_dir:
                    plan_file = spec_dir / "implementation_plan.json"
                    if plan_file.exists():
                        plan = json.loads(plan_file.read_text())
                        # Extract all subtasks from all phases
                        phases = plan.get("phases", [])
                        for phase in phases:
                            phase_subtasks = phase.get("subtasks", [])
                            for subtask in phase_subtasks:
                                subtasks_data.append({
                                    "id": subtask.get("id", ""),
                                    "status": subtask.get("status", "pending"),
                                    "title": subtask.get("description", ""),
                                })
            except Exception as e:
                import logging
                logging.getLogger(__name__).debug(f"[AgentService] Could not read subtasks for {progress.task_id}: {e}")

            await emit_task_update(progress.task_id, {
                "executionProgress": {
                    "phase": phase_value,
                    "phaseProgress": phase_progress,
                    "overallProgress": overall_progress,
                    "currentSubtask": progress.subtask,
                    "message": progress.message,
                    "sequenceNumber": sequence_number,
                    "startedAt": started_at,
                },
                "phase": phase_value,
                "subtasksCompleted": progress.subtask_index,
                "subtasksTotal": progress.subtask_total,
                "subtasks": subtasks_data,  # Include subtasks array for frontend
            })

            # If phase changed, also emit status change for kanban column movement
            if previous_phase is not None and progress.phase != previous_phase:
                new_status = phase_to_status(progress.phase)
                review_reason = phase_to_review_reason(progress.phase)
                await emit_task_status(progress.task_id, new_status, review_reason)

        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"[AgentService] WebSocket broadcast failed: {e}")

        # Also emit to local callbacks
        callbacks = self._progress_callbacks.get(progress.task_id, [])
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(progress)
                else:
                    callback(progress)
            except Exception:
                pass

    def _parse_phase_event(self, line: str) -> dict | None:
        """Parse phase event from agent output.

        Supports two formats:
        1. [PHASE_EVENT] phase=coding message="Starting"
        2. __EXEC_PHASE__:{"phase":"coding","message":"Starting","progress":50}
        """
        # Check for __EXEC_PHASE__: prefix (JSON format from backend)
        exec_phase_prefix = "__EXEC_PHASE__:"
        if line.startswith(exec_phase_prefix):
            try:
                json_str = line[len(exec_phase_prefix):]
                event = json.loads(json_str)
                # Map 'progress' to 'percentage' for consistency
                if "progress" in event:
                    event["percentage"] = event.pop("progress")
                return event
            except json.JSONDecodeError:
                return None

        # Check for [PHASE_EVENT] prefix (key=value format)
        match = re.match(r"\[PHASE_EVENT\]\s*(.+)", line)
        if not match:
            return None

        event_str = match.group(1)
        event = {}

        # Parse key=value pairs
        for part in re.findall(r"(\w+)=([^\s]+|\"[^\"]+\")", event_str):
            key, value = part
            value = value.strip('"')
            event[key] = value

        return event if event else None

    async def _process_output(
        self,
        task_id: str,
        stream: asyncio.StreamReader,
        is_stderr: bool = False,
        log_writer: TaskLogWriter | None = None,
        spec_id: str | None = None,
    ) -> TaskPhase:
        """Process output stream from subprocess.

        Returns the final phase detected.
        """
        import logging
        logger = logging.getLogger(__name__)
        current_phase = TaskPhase.SPEC_CREATION

        async for line_bytes in stream:
            line = line_bytes.decode("utf-8", errors="replace").rstrip()

            # Log stderr to server logs for debugging
            if is_stderr and line:
                logger.warning(f"[AgentService] Task {task_id} stderr: {line}")

            # Create log entry
            log = TaskLog(
                task_id=task_id,
                content=line,
                source="stderr" if is_stderr else "stdout",
                level="error" if is_stderr else "info",
            )
            await self._emit_log(log)

            # Detect rate limit messages to trigger failover after exit
            if self._is_rate_limit_line(line):
                self._task_rate_limits[task_id] = True
                logger.warning(f"[AgentService] Rate limit detected for task {task_id} (will attempt failover if enabled)")

            # Write to task_logs.json for detailed phase logs
            if log_writer and spec_id and not is_stderr:
                log_writer.process_line(spec_id, current_phase, line)

            # Check for phase events (__EXEC_PHASE__: or [PHASE_EVENT])
            event = self._parse_phase_event(line)
            if event:
                phase_str = event.get("phase", "")
                phase_map = {
                    "spec_creation": TaskPhase.SPEC_CREATION,
                    "planning": TaskPhase.PLANNING,
                    "coding": TaskPhase.CODING,
                    "qa_review": TaskPhase.QA_REVIEW,
                    "qa_fixing": TaskPhase.QA_FIXING,
                    "complete": TaskPhase.COMPLETED,  # backend uses "complete"
                    "completed": TaskPhase.COMPLETED,
                    "failed": TaskPhase.FAILED,
                }
                old_phase = current_phase
                if phase_str in phase_map:
                    current_phase = phase_map[phase_str]

                    # Track current phase for proper status on task completion
                    self._task_current_phases[task_id] = current_phase

                    # Update log writer phase status
                    if log_writer and spec_id:
                        if old_phase != current_phase:
                            log_writer.set_phase_status(spec_id, old_phase, "completed")
                        # For COMPLETED/FAILED phases, don't set them as "active" - just mark previous complete
                        if current_phase not in (TaskPhase.COMPLETED, TaskPhase.FAILED):
                            log_writer.set_phase_status(spec_id, current_phase, "active")
                        # Ensure validation phase is properly marked completed when task completes
                        if current_phase == TaskPhase.COMPLETED and old_phase == TaskPhase.QA_REVIEW:
                            log_writer.set_phase_status(spec_id, TaskPhase.QA_REVIEW, "completed")

                # Always emit progress for phase events (even if phase didn't change)
                progress = TaskProgress(
                    task_id=task_id,
                    phase=current_phase,
                    message=event.get("message", ""),
                    subtask=event.get("subtask"),
                    subtask_index=int(event["subtask_index"]) if "subtask_index" in event else None,
                    subtask_total=int(event["subtask_total"]) if "subtask_total" in event else None,
                    percentage=event.get("percentage"),  # Include percentage from event
                    data=event,
                )
                # Pass previous phase if it changed, so status event can be emitted
                await self._emit_progress(progress, previous_phase=old_phase if old_phase != current_phase else None)

            # Check for JSON progress data
            if line.startswith("{"):
                try:
                    data = json.loads(line)
                    if "phase" in data or "status" in data:
                        phase_str = data.get("phase", data.get("status", ""))
                        if phase_str in ["coding", "planning", "qa_review", "qa_fixing"]:
                            old_phase = current_phase
                            current_phase = TaskPhase(phase_str)

                            # Track current phase for proper status on task completion
                            self._task_current_phases[task_id] = current_phase

                            # Update log writer phase status
                            if log_writer and spec_id:
                                if old_phase != current_phase:
                                    log_writer.set_phase_status(spec_id, old_phase, "completed")
                                log_writer.set_phase_status(spec_id, current_phase, "active")

                        progress = TaskProgress(
                            task_id=task_id,
                            phase=current_phase,
                            message=data.get("message", ""),
                            subtask=data.get("subtask"),
                            subtask_index=data.get("subtask_index"),
                            subtask_total=data.get("subtask_total"),
                            percentage=data.get("percentage"),
                            data=data,
                        )
                        # Pass previous phase if it changed, so status event can be emitted
                        await self._emit_progress(progress, previous_phase=old_phase if old_phase != current_phase else None)
                except json.JSONDecodeError:
                    pass

        return current_phase

    async def _sync_worktree_files(self, project_path: Path, spec_id: str, task_id: str | None = None) -> None:
        """Sync files from worktree spec dir to main spec dir for frontend visibility.

        Args:
            project_path: Path to the project
            spec_id: Spec directory name (e.g., "001-fix-bug")
            task_id: Full task ID (project_id:spec_id) for consistent tracking. Falls back to spec_id if not provided.
        """
        # Use task_id for tracking if provided, otherwise fall back to spec_id for backwards compatibility
        tracking_key = task_id or spec_id
        import logging
        logger = logging.getLogger(__name__)

        # Paths
        worktree_spec = project_path / ".magestic-ai" / "worktrees" / "tasks" / spec_id / ".magestic-ai" / "specs" / spec_id
        main_spec = project_path / ".magestic-ai" / "specs" / spec_id

        # Ensure main spec dir exists
        main_spec.mkdir(parents=True, exist_ok=True)

        # Files to sync (in order of priority)
        files_to_sync = [
            "implementation_plan.json",  # Most critical for UI
            "task_logs.json",  # Detailed phase logs for UI
            "build-progress.txt",
            "context.json",
            "qa_report.md",
            "QA_FIX_REQUEST.md",
            "spec.md",
            "requirements.json",
        ]

        # Directories to sync (will copy entire directory tree)
        dirs_to_sync = [
            "memory",  # Session insights and memory data
        ]

        synced_count = 0
        for filename in files_to_sync:
            src = worktree_spec / filename
            dst = main_spec / filename
            if src.exists():
                try:
                    # For implementation_plan.json, preserve status and reviewReason from main spec
                    # These fields are set by _update_plan_status and shouldn't be overwritten
                    if filename == "implementation_plan.json" and dst.exists():
                        try:
                            main_plan = json.loads(dst.read_text())
                            worktree_plan = json.loads(src.read_text())
                            # Preserve status/reviewReason from main spec if present
                            preserved_status = main_plan.get("status")
                            preserved_reason = main_plan.get("reviewReason")
                            # Copy worktree plan (has updated subtask statuses)
                            shutil.copy2(src, dst)
                            # Restore preserved fields if they exist
                            if preserved_status or preserved_reason:
                                merged_plan = json.loads(dst.read_text())
                                if preserved_status:
                                    merged_plan["status"] = preserved_status
                                if preserved_reason:
                                    merged_plan["reviewReason"] = preserved_reason
                                dst.write_text(json.dumps(merged_plan, indent=2))
                        except (json.JSONDecodeError, OSError) as merge_err:
                            logger.warning(f"[AgentService] Failed to merge implementation_plan.json, falling back to copy: {merge_err}")
                            shutil.copy2(src, dst)
                    else:
                        shutil.copy2(src, dst)
                    synced_count += 1
                except Exception as e:
                    logger.warning(f"[AgentService] Failed to sync {filename}: {e}")

        # Sync directories
        for dirname in dirs_to_sync:
            src_dir = worktree_spec / dirname
            dst_dir = main_spec / dirname
            if src_dir.exists() and src_dir.is_dir():
                try:
                    # Remove existing and copy fresh
                    if dst_dir.exists():
                        shutil.rmtree(dst_dir)
                    shutil.copytree(src_dir, dst_dir)
                    synced_count += 1
                except Exception as e:
                    logger.warning(f"[AgentService] Failed to sync directory {dirname}: {e}")

        if synced_count > 0:
            logger.debug(f"[AgentService] Synced {synced_count} files from worktree to main spec dir")

        # Always check for subtask status changes and emit WebSocket updates
        # This runs independently of file sync to ensure real-time updates
        try:
            # Read implementation plan for progress info
            plan_file = main_spec / "implementation_plan.json"
            if plan_file.exists():
                plan = json.loads(plan_file.read_text())

                # Calculate progress from subtasks in phases
                all_subtasks = []
                current_phase = None
                for phase in plan.get("phases", []):
                    if phase.get("status") == "in_progress":
                        current_phase = phase.get("name")
                    all_subtasks.extend(phase.get("subtasks", []))

                completed = sum(1 for s in all_subtasks if s.get("status") == "completed")
                total = len(all_subtasks)
                progress = int((completed / total) * 100) if total > 0 else 0

                # Find current subtask
                current_subtask = None
                for s in all_subtasks:
                    if s.get("status") == "in_progress":
                        current_subtask = s.get("description", s.get("id"))
                        break

                # Build subtasks array for real-time frontend updates
                subtasks_data = [
                    {"id": s.get("id"), "status": s.get("status")}
                    for s in all_subtasks
                ]

                # Detect individual subtask status changes and emit granular events
                # This enables real-time subtask checkbox updates in the frontend
                previous_states = self._task_subtask_states.get(tracking_key, {})
                current_states = {s.get("id"): s.get("status") for s in all_subtasks}

                # Check for changes and emit individual events
                has_changes = False
                for subtask_id, current_status in current_states.items():
                    previous_status = previous_states.get(subtask_id)
                    if previous_status != current_status:
                        has_changes = True
                        # Subtask status changed - emit granular event
                        await emit_subtask_update(
                            task_id=spec_id,
                            subtask_id=subtask_id,
                            status=current_status,
                            previous_status=previous_status
                        )

                # Update tracking for next comparison
                self._task_subtask_states[tracking_key] = current_states

                # Only emit task update if there were changes (to avoid flooding)
                if has_changes or synced_count > 0:
                    # Emit task update
                    await emit_task_update(spec_id, {
                        "executionProgress": {
                            "phase": "coding",  # Default to coding during execution
                            "phaseProgress": progress,
                            "overallProgress": scale_progress("coding", progress),
                            "currentSubtask": current_subtask,
                            "message": f"{completed}/{total} subtasks completed",
                        },
                        "phase": current_phase,
                        "subtasksCompleted": completed,
                        "subtasksTotal": total,
                        "subtasks": subtasks_data,
                    })
        except Exception as e:
            logger.warning(f"[AgentService] Failed to emit task update: {e}")

    async def _monitor_process(
        self,
        task_id: str,
        proc: asyncio.subprocess.Process,
        project_path: Path | None = None,
        spec_id: str | None = None,
        cmd: list[str] | None = None,
        env: dict | None = None
    ) -> None:
        """Monitor subprocess and clean up when it finishes.

        Also periodically syncs files from worktree to main spec dir if project_path and spec_id are provided.
        Supports profile failover on early failures when cmd and env are provided.
        """
        import logging
        logger = logging.getLogger(__name__)

        try:
            # Periodic sync loop (every 3 seconds) while process is running
            sync_interval = 3.0

            rate_limit_forced_restart = False
            return_code: int | None = None

            while True:
                # Check if process has finished
                try:
                    return_code = await asyncio.wait_for(proc.wait(), timeout=sync_interval)
                    # Process finished
                    break
                except asyncio.TimeoutError:
                    # Process still running, sync files
                    if project_path and spec_id:
                        await self._sync_worktree_files(project_path, spec_id, task_id)

                    # Fix Bug #3: For spec creation, check if review checkpoint reached while process is running
                    if project_path and not spec_id:
                        # Detect if spec_runner created plan_review.html (review checkpoint reached)
                        # Parse spec_id from task_id (format: "project_id:spec_id")
                        detected_spec_id = None
                        if ":" in task_id:
                            _, detected_spec_id = task_id.split(":", 1)

                        if detected_spec_id:
                            detected_spec_dir = project_path / ".magestic-ai" / "specs" / detected_spec_id
                            plan_review_file = detected_spec_dir / "plan_review.html"

                            # Check if plan_review.html exists (indicates review checkpoint reached)
                            if plan_review_file.exists():
                                # Check if we've already emitted PLAN_REVIEW for this task
                                current_phase = self._task_current_phases.get(task_id)
                                if current_phase != TaskPhase.PLAN_REVIEW:
                                    logger.info(f"[AgentService] Detected review checkpoint for {detected_spec_id} (plan_review.html exists)")

                                    # Update plan status to human_review
                                    await self._update_plan_status(project_path, detected_spec_id, "human_review", task_id)

                                    # Emit PLAN_REVIEW phase (maps to "human_review" status) — plan_review always scales to 20%
                                    await self._emit_progress(
                                        TaskProgress(
                                            task_id=task_id,
                                            phase=TaskPhase.PLAN_REVIEW,
                                            message="Spec created - waiting for human approval",
                                            percentage=100,
                                        ),
                                        previous_phase=TaskPhase.SPEC_CREATION,  # Enable status event emission
                                    )

                                    # Mark phase as emitted
                                    self._task_current_phases[task_id] = TaskPhase.PLAN_REVIEW
                                    logger.info(f"[AgentService] Emitted PLAN_REVIEW status for {task_id}")

                    # If we detect a rate limit and failover is enabled, don't wait for the process to exit.
                    if cmd and env:
                        profile_info = self._task_profiles.get(task_id, {})
                        attempt = profile_info.get("attempt", 1)
                        rate_limit_detected = self._task_rate_limits.get(task_id, False)

                        if (
                            rate_limit_detected
                            and attempt == 1
                            and self._should_retry_with_failover()
                        ):
                            logger.warning(
                                f"[AgentService] Rate limit detected for {task_id} while running; terminating process to trigger profile failover"
                            )
                            rate_limit_forced_restart = True
                            try:
                                proc.terminate()
                            except Exception:
                                pass
                            try:
                                return_code = await proc.wait()
                            except Exception:
                                return_code = 1
                            break

            if return_code is None:
                return_code = 1
            if rate_limit_forced_restart and return_code == 0:
                # Ensure we trigger the retry path.
                return_code = 1

            # Process exited - do final sync
            if project_path and spec_id:
                await self._sync_worktree_files(project_path, spec_id, task_id)

            logger.info(f"[AgentService] Task {task_id} process exited with code {return_code}")

            # Special case: Spec creation (project_path provided, spec_id is None)
            # Need to detect the created spec_id and check if it requires review
            if project_path and not spec_id:
                logger.info("[AgentService] Spec creation completed, detecting created spec...")
                try:
                    specs_dir = project_path / ".magestic-ai" / "specs"
                    if specs_dir.exists():
                        # Find the newest spec directory (just created)
                        spec_dirs = sorted(
                            [d for d in specs_dir.iterdir() if d.is_dir()],
                            key=lambda d: d.stat().st_mtime,
                            reverse=True
                        )
                        if spec_dirs:
                            detected_spec_dir = spec_dirs[0]
                            detected_spec_id = detected_spec_dir.name
                            logger.info(f"[AgentService] Detected created spec: {detected_spec_id}")

                            # Check if this spec requires review
                            review_state_file = detected_spec_dir / "review_state.json"
                            if review_state_file.exists():
                                review_data = json.loads(review_state_file.read_text())
                                if not review_data.get("approved", False):
                                    # Spec creation completed, now waiting for review
                                    logger.info(f"[AgentService] Spec {detected_spec_id} requires human review")

                                    # Update plan status to human_review
                                    await self._update_plan_status(project_path, detected_spec_id, "human_review", task_id)

                                    # Clean up tracking data
                                    if task_id in self.running_tasks:
                                        del self.running_tasks[task_id]
                                    self._task_sequence_numbers.pop(task_id, None)
                                    self._task_start_times.pop(task_id, None)
                                    self._task_current_phases.pop(task_id, None)
                                    self._task_profiles.pop(task_id, None)
                                    self._task_subtask_states.pop(task_id, None)

                                    # Emit PLAN_REVIEW phase (maps to "human_review" status) — plan_review always scales to 20%
                                    await self._emit_progress(
                                        TaskProgress(
                                            task_id=task_id,
                                            phase=TaskPhase.PLAN_REVIEW,
                                            message="Spec created - waiting for human approval",
                                            percentage=100,
                                        ),
                                        previous_phase=TaskPhase.SPEC_CREATION,  # Enable status event emission
                                    )

                                    logger.info(f"[AgentService] Spec {detected_spec_id} transitioned to PLAN_REVIEW phase")
                                    return  # Exit early - not a failure

                            # If we reach here, spec was created but doesn't need review
                            # Emit completion event
                            logger.info(f"[AgentService] Spec {detected_spec_id} created successfully (no review required)")

                            # Persist status to implementation_plan.json
                            await self._update_plan_status(project_path, detected_spec_id, "completed", task_id)

                            # Clean up tracking data
                            if task_id in self.running_tasks:
                                del self.running_tasks[task_id]
                            self._task_sequence_numbers.pop(task_id, None)
                            self._task_start_times.pop(task_id, None)
                            self._task_current_phases.pop(task_id, None)
                            self._task_profiles.pop(task_id, None)
                            self._task_rate_limits.pop(task_id, None)
                            self._task_subtask_states.pop(task_id, None)

                            # Emit completion (20% overall = planning complete, override scaling
                            # since COMPLETED phase would normally scale to 95-100%)
                            await self._emit_progress(
                                TaskProgress(
                                    task_id=task_id,
                                    phase=TaskPhase.COMPLETED,
                                    message="Spec created successfully",
                                    percentage=100,
                                    overall_progress=20,
                                ),
                                previous_phase=TaskPhase.SPEC_CREATION,
                            )
                            return  # Exit early
                except Exception as e:
                    logger.warning(f"[AgentService] Failed to detect created spec: {e}")
                    # Fall through to normal completion handling

            # Check if task is waiting for review (can exit with code 0 or 1)
            # Code 0: auto_continue mode (web UI) - exits cleanly after saving review state
            # Code 1: CLI mode - exits with error when blocked (legacy behavior)
            if project_path and spec_id:
                spec_dir = project_path / ".magestic-ai" / "specs" / spec_id
                review_state_file = spec_dir / "review_state.json"

                # If review_state.json exists with approved=false, task is waiting for human review
                if review_state_file.exists():
                    try:
                        review_data = json.loads(review_state_file.read_text())
                        if not review_data.get("approved", False):
                            # This is NOT a failure - it's waiting for human review!
                            logger.info(f"[AgentService] Task {task_id} awaiting human review (not a failure)")

                            # Get actual phase BEFORE cleanup
                            actual_phase = self._get_current_phase(task_id)

                            # Finalize log writers for the phase we were in
                            if task_id in self._task_log_writers:
                                log_writer, main_log_writer = self._task_log_writers[task_id]
                                if spec_id:
                                    log_writer.finalize(spec_id, actual_phase)
                                    log_writer.set_phase_status(spec_id, actual_phase, "completed")
                                    main_log_writer.finalize(spec_id, actual_phase)
                                    main_log_writer.set_phase_status(spec_id, actual_phase, "completed")
                                del self._task_log_writers[task_id]

                            # Update plan status to human_review
                            await self._update_plan_status(project_path, spec_id, "human_review", task_id)

                            # Clean up tracking data
                            if task_id in self.running_tasks:
                                del self.running_tasks[task_id]
                            self._task_sequence_numbers.pop(task_id, None)
                            self._task_start_times.pop(task_id, None)
                            self._task_current_phases.pop(task_id, None)
                            self._task_profiles.pop(task_id, None)
                            self._task_subtask_states.pop(task_id, None)
                            self._spec_dirs.pop(task_id, None)

                            # Emit PLAN_REVIEW phase (maps to "human_review" status)
                            await self._emit_progress(
                                TaskProgress(
                                    task_id=task_id,
                                    phase=TaskPhase.PLAN_REVIEW,
                                    message="Plan created - waiting for human approval",
                                ),
                                previous_phase=actual_phase,  # Enable status event emission
                            )

                            logger.info(f"[AgentService] Task {task_id} transitioned to PLAN_REVIEW phase")
                            return  # Exit early - not a failure

                    except (json.JSONDecodeError, OSError) as e:
                        logger.debug(f"[AgentService] Could not read review_state.json: {e}")
                        # Fall through to treat as actual failure

            # Check for early failure and attempt profile failover
            if return_code != 0 and project_path and spec_id and cmd and env:
                spec_dir = project_path / ".magestic-ai" / "specs" / spec_id

                # Check if this is an early failure (no logs written)
                is_early = self._is_early_failure(spec_dir, return_code)
                rate_limit_detected = self._task_rate_limits.get(task_id, False)

                # Check if we should retry (settings enabled + first attempt)
                profile_info = self._task_profiles.get(task_id, {})
                attempt = profile_info.get("attempt", 1)
                should_retry = (
                    (is_early or rate_limit_detected)
                    and attempt == 1  # Only retry once
                    and self._should_retry_with_failover()
                )

                if should_retry:
                    failed_profile_id = profile_info.get("profileId")
                    reason = "rate_limit" if rate_limit_detected else "early_failure"
                    logger.info(f"[AgentService] {reason.replace('_', ' ')} detected for {task_id}, attempting profile failover")

                    # Attempt retry with different profile
                    if not failed_profile_id:
                        logger.warning(f"[AgentService] No failed profile recorded for {task_id}; cannot failover")
                        new_proc = None
                    else:
                        new_proc = await self._retry_task_with_profile(
                            task_id, project_path, spec_id, cmd, env, failed_profile_id, reason
                        )

                    if new_proc:
                        # Clear the flag for the new attempt so it can detect rate limits again.
                        self._task_rate_limits.pop(task_id, None)

                        # Update running task reference
                        self.running_tasks[task_id] = new_proc

                        # Get log writers for output processing
                        log_writer = None
                        main_log_writer = None
                        if task_id in self._task_log_writers:
                            log_writer, main_log_writer = self._task_log_writers[task_id]

                        # Restart output processing for new subprocess
                        asyncio.create_task(
                            self._process_output(
                                task_id,
                                new_proc.stdout,
                                is_stderr=False,
                                log_writer=log_writer,
                                spec_id=spec_id,
                            )
                        )
                        asyncio.create_task(
                            self._process_output(
                                task_id,
                                new_proc.stderr,
                                is_stderr=True,
                                log_writer=log_writer,
                                spec_id=spec_id,
                            )
                        )

                        # Restart monitoring for new subprocess (without cmd/env to prevent infinite retry)
                        asyncio.create_task(
                            self._monitor_process(
                                task_id,
                                new_proc,
                                project_path,
                                spec_id,
                                cmd=None,  # Prevent second retry
                                env=None   # Prevent second retry
                            )
                        )

                        logger.info(f"[AgentService] Task {task_id} restarted with alternate profile")
                        return  # Exit this monitor instance
                    else:
                        logger.warning(f"[AgentService] No alternate profile available for task {task_id}, surfacing failure")

            # Get actual phase BEFORE cleanup (needed for proper status emission)
            actual_phase = self._get_current_phase(task_id)
            final_status = "completed" if return_code == 0 else "failed"

            # Finalize and clean up log writers
            if task_id in self._task_log_writers:
                log_writer, main_log_writer = self._task_log_writers[task_id]

                # Finalize both log writers - set status on the phase the task was actually in
                if spec_id:
                    log_writer.finalize(spec_id, actual_phase)
                    log_writer.set_phase_status(spec_id, actual_phase, final_status)
                    main_log_writer.finalize(spec_id, actual_phase)
                    main_log_writer.set_phase_status(spec_id, actual_phase, final_status)

                del self._task_log_writers[task_id]
                logger.debug(f"[AgentService] Finalized task logs for {task_id}")

            # Update implementation_plan.json status for frontend display
            if spec_id and project_path:
                status = "completed" if return_code == 0 else "failed"
                logger.info(f"[AgentService._monitor_process] About to call _update_plan_status: spec_id={spec_id}, status={status}, task_id={task_id}, project_path={project_path}")
                await self._update_plan_status(project_path, spec_id, status, task_id)
                logger.info(f"[AgentService._monitor_process] _update_plan_status call completed")

            # Clean up from running_tasks and tracking data
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
            self._task_sequence_numbers.pop(task_id, None)
            self._task_start_times.pop(task_id, None)
            self._task_current_phases.pop(task_id, None)
            self._task_profiles.pop(task_id, None)
            self._task_rate_limits.pop(task_id, None)
            self._task_subtask_states.pop(task_id, None)
            self._spec_dirs.pop(task_id, None)

            # Send email/in-app notifications on task completion or failure
            _notif_user_id = self._task_user_ids.pop(task_id, "")

            # Emit completion/failure progress with previous_phase to trigger status event (Bug 1 fix)
            if return_code == 0:
                await self._emit_progress(
                    TaskProgress(
                        task_id=task_id,
                        phase=TaskPhase.COMPLETED,
                        message="Task completed successfully",
                    ),
                    previous_phase=actual_phase,  # Enable status event emission
                )
                if _notif_user_id:
                    try:
                        from .notification_service import notification_service
                        _proj_name = project_path.name if project_path else ""
                        _proj_id = task_id.split(":")[0] if ":" in task_id else ""
                        await notification_service.notify(
                            user_id=_notif_user_id,
                            type="task_complete",
                            title=f"Task completed: {spec_id}",
                            message=f"Task {spec_id} in project {_proj_name} completed successfully.",
                            data={"task_id": task_id, "project_id": _proj_id},
                        )
                    except Exception:
                        logger.debug("Failed to send task completion notification", exc_info=True)
            else:
                logger.error(f"[AgentService] Task {task_id} failed with exit code {return_code}")
                await self._emit_progress(
                    TaskProgress(
                        task_id=task_id,
                        phase=TaskPhase.FAILED,
                        message=f"Task failed with exit code {return_code}",
                    ),
                    previous_phase=actual_phase,  # Enable status event emission
                )
                if _notif_user_id:
                    try:
                        from .notification_service import notification_service
                        _proj_name = project_path.name if project_path else ""
                        _proj_id = task_id.split(":")[0] if ":" in task_id else ""
                        await notification_service.notify(
                            user_id=_notif_user_id,
                            type="task_failed",
                            title=f"Task failed: {spec_id}",
                            message=f"Task {spec_id} in project {_proj_name} failed with exit code {return_code}.",
                            data={"task_id": task_id, "project_id": _proj_id},
                        )
                    except Exception:
                        logger.debug("Failed to send task failure notification", exc_info=True)
        except asyncio.CancelledError:
            # Task was cancelled, cleanup already handled by stop_task
            pass
        except Exception as e:
            # Unexpected error, ensure cleanup
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
            self._task_sequence_numbers.pop(task_id, None)
            self._task_start_times.pop(task_id, None)
            self._task_user_ids.pop(task_id, None)
            self._task_profiles.pop(task_id, None)
            self._task_rate_limits.pop(task_id, None)
            self._task_subtask_states.pop(task_id, None)
            await self._emit_progress(TaskProgress(
                task_id=task_id,
                phase=TaskPhase.FAILED,
                message=f"Task monitoring error: {e}",
            ))

    async def _update_plan_status(self, project_path: Path, spec_id: str, status: str, task_id: str) -> None:
        """Update the status field in implementation_plan.json after task completion.

        This ensures the frontend displays the correct task status in the kanban board.
        Also emits a WebSocket event so the frontend updates in real-time.
        """
        import logging
        logger = logging.getLogger(__name__)
        plan_file = project_path / ".magestic-ai" / "specs" / spec_id / "implementation_plan.json"
        logger.info(f"[AgentService._update_plan_status] CALLED for spec_id={spec_id}, status={status}, task_id={task_id}")
        logger.info(f"[AgentService._update_plan_status] plan_file path: {plan_file}")
        logger.info(f"[AgentService._update_plan_status] plan_file exists: {plan_file.exists()}")
        if not plan_file.exists():
            logger.warning(f"[AgentService._update_plan_status] plan_file does not exist, returning early")
            return

        try:
            plan = json.loads(plan_file.read_text())

            # Don't overwrite if user explicitly marked task as done via kanban
            if plan.get("status") == "done":
                logger.info(f"[AgentService._update_plan_status] Plan status is 'done' (user-set), skipping overwrite for {spec_id}")
                return

            # Fix 2: Validate that the plan is not just a minimal status object
            # A valid plan should have phases and subtasks from spec creation
            if "phases" not in plan or not plan.get("phases"):
                logger.error(f"[AgentService] Invalid or minimal implementation plan detected for {spec_id}")
                await emit_task_status(task_id, "failed", "invalid_plan")
                return

            # Map internal status to frontend-compatible status using the canonical helpers
            phase_enum_map = {
                "completed": TaskPhase.COMPLETED,
                "failed": TaskPhase.FAILED,
                "human_review": TaskPhase.PLAN_REVIEW,
            }
            phase_enum = phase_enum_map.get(status)
            if phase_enum:
                plan["status"] = phase_to_status(phase_enum)
                review_reason = phase_to_review_reason(phase_enum)
                if review_reason:
                    plan["reviewReason"] = review_reason
            else:
                plan["status"] = status

            logger.info(f"[AgentService._update_plan_status] About to write file with status={plan.get('status')}, reviewReason={plan.get('reviewReason')}")
            plan_file.write_text(json.dumps(plan, indent=2))
            logger.info(f"[AgentService._update_plan_status] Successfully wrote plan_file")
            logger.info(f"[AgentService] Updated plan status to '{plan['status']}' for {spec_id}")

            # Extract subtasks for WebSocket broadcast
            subtasks_data = []
            phases = plan.get("phases", [])
            for phase in phases:
                phase_subtasks = phase.get("subtasks", [])
                for subtask in phase_subtasks:
                    subtasks_data.append({
                        "id": subtask.get("id", ""),
                        "status": subtask.get("status", "pending"),
                        "title": subtask.get("description", ""),
                    })

            # Emit WebSocket events so frontend updates in real-time
            review_reason = plan.get("reviewReason")
            # First emit status change
            await emit_task_status(task_id, plan["status"], review_reason)
            # Then emit task update with subtasks so they appear immediately in UI
            await emit_task_update(task_id, {
                "subtasks": subtasks_data,
                "subtasksCompleted": sum(1 for s in subtasks_data if s["status"] == "completed"),
                "subtasksTotal": len(subtasks_data),
            })
        except Exception as e:
            logger.error(f"[AgentService] Failed to update plan status: {e}")

    async def start_spec_creation(
        self,
        task_id: str,
        project_path: Path,
        title: str,
        description: str,
        complexity: str | None = None,
        auto_continue: bool = True,
    ) -> asyncio.subprocess.Process:
        """Start spec creation for a task."""
        import logging
        logger = logging.getLogger(__name__)
        if task_id in self.running_tasks:
            raise ValueError(f"Task {task_id} is already running")

        # Parse spec_id from task_id (format: "project_id:spec_id")
        if ":" in task_id:
            _, spec_id = task_id.split(":", 1)
            spec_dir = project_path / ".magestic-ai" / "specs" / spec_id
        else:
            # Fallback: no project ID prefix (shouldn't happen in web mode)
            spec_dir = None

        # Fix 5: Check if task requires manual review before coding
        # If requireReviewBeforeCoding is true, DON'T auto-approve (let user review the plan)
        should_auto_approve = True  # Default for web mode
        if spec_dir:
            task_metadata_file = spec_dir / "task_metadata.json"
            if task_metadata_file.exists():
                try:
                    import json
                    metadata = json.loads(task_metadata_file.read_text())
                    if metadata.get("requireReviewBeforeCoding", False):
                        should_auto_approve = False
                        logger.info(f"[AgentService] Task {task_id} requires manual review - NOT auto-approving spec")
                except (json.JSONDecodeError, OSError) as e:
                    logger.warning(f"[AgentService] Failed to read task_metadata.json: {e}")

        # Build command
        cmd = [
            sys.executable,
            str(self.backend_path / "runners" / "spec_runner.py"),
            "--task", f"{title}\n\n{description}",
            "--project-dir", str(project_path),
        ]

        # Fix 1: Only auto-approve if task doesn't require manual review
        if should_auto_approve:
            cmd.append("--auto-approve")

        # Fix 4: Pass existing spec directory to prevent duplicate task creation
        if spec_dir:
            cmd.extend(["--spec-dir", str(spec_dir)])

        if complexity:
            cmd.extend(["--complexity", complexity])

        # Set environment
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        # Run Claude in non-interactive mode - bypass permission prompts
        env["CLAUDE_CODE_ENTRYPOINT"] = "cli"  # Signal non-interactive mode
        env["CI"] = "true"  # Many CLI tools use this to detect non-interactive mode

        # Quick Mode for simple tasks (safety net if simple task reaches spec creation)
        if complexity == "simple":
            env["QUICK_MODE"] = "true"
            logger.info(f"[AgentService] Quick Mode enabled for spec creation task {task_id}")

        # Load backend .env file for graphiti and other settings
        backend_env_file = self.backend_path / ".env"
        if backend_env_file.exists():
            try:
                with open(backend_env_file) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip()
                            # Don't override existing env vars
                            if key not in env:
                                env[key] = value
                logger.info("[AgentService] Loaded backend .env for spec creation")
            except Exception as e:
                logger.warning(f"[AgentService] Failed to load backend .env: {e}")

        # Load project .magestic-ai/.env for project-level settings (USE_CLAUDE_MD, etc.)
        project_env_file = project_path / ".magestic-ai" / ".env"
        if project_env_file.exists():
            try:
                with open(project_env_file) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip()
                            if key not in env:
                                env[key] = value
                logger.info("[AgentService] Loaded project .env for spec creation")
            except Exception as e:
                logger.warning(f"[AgentService] Failed to load project .env: {e}")

        # Get OAuth token with profile tracking
        token, profile_id, profile_name = self._resolve_claude_token()
        if token:
            env["CLAUDE_CODE_OAUTH_TOKEN"] = token
            logger.info(
                f"[AgentService] Using Claude profile for spec creation: {profile_name} ({profile_id})"
            )
            # Store for potential retry tracking
            self._task_profiles[task_id] = {
                "profileId": profile_id,
                "profileName": profile_name,
                "attempt": 1,
            }
        else:
            logger.warning("[AgentService] No Claude OAuth token available for spec creation")

        # Start subprocess with a pseudo-TTY to prevent "Stream closed" errors
        # Claude Code CLI expects a TTY for permission handling
        import pty

        master_fd, slave_fd = pty.openpty()

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=slave_fd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(project_path),
            env=env,
        )

        # Close slave fd in parent process
        os.close(slave_fd)

        self.running_tasks[task_id] = proc

        # Initialize tracking for sequence numbers and start time
        self._task_sequence_numbers[task_id] = 0
        self._task_start_times[task_id] = datetime.now().isoformat()
        if user_id:
            self._task_user_ids[task_id] = user_id
        # Store spec directory for reading implementation plans during progress updates
        self._spec_dirs[task_id] = spec_dir

        # Emit initial progress (50% within spec_creation phase → 10% overall)
        await self._emit_progress(TaskProgress(
            task_id=task_id,
            phase=TaskPhase.SPEC_CREATION,
            message="Starting spec creation...",
            percentage=50,
        ))

        # Start output processing in background
        asyncio.create_task(self._process_output(task_id, proc.stdout, is_stderr=False))
        asyncio.create_task(self._process_output(task_id, proc.stderr, is_stderr=True))

        # Start process monitor to clean up when finished
        # Pass project_path so monitor can detect created spec and check for review state
        asyncio.create_task(self._monitor_process(task_id, proc, project_path=project_path))

        return proc

    async def start_task_execution(
        self,
        task_id: str,
        project_path: Path,
        spec_id: str,
        auto_continue: bool = True,
        base_branch: str | None = None,
        mode: str | None = "full",
        force: bool = False,
        user_id: str = "",
    ) -> asyncio.subprocess.Process:
        """Start task execution (run.py).

        Args:
            mode: "quick" for simplified prompts (~70% fewer tokens), "full" for comprehensive prompts.
            force: If True, bypasses approval checks (use when plan was already manually approved).
        """
        import logging
        logger = logging.getLogger(__name__)

        if task_id in self.running_tasks:
            raise ValueError(f"Task {task_id} is already running")

        # Build command
        cmd = [
            sys.executable,
            str(self.backend_path / "run.py"),
            "--spec", spec_id,
            "--project-dir", str(project_path),
        ]

        if auto_continue:
            cmd.append("--auto-continue")

            # Check if human review before coding is required
            # If so, don't pass --force to allow the approval gate
            spec_dir = project_path / ".magestic-ai" / "specs" / spec_id
            requirements_file = spec_dir / "requirements.json"
            task_metadata_file = spec_dir / "task_metadata.json"
            require_review = False

            # Sync metadata from requirements.json to task_metadata.json (Bug fix)
            # Frontend writes to requirements.json, backend reads task_metadata.json
            # Ensure they stay in sync to prevent requireReviewBeforeCoding mismatches
            if requirements_file.exists():
                try:
                    import json
                    requirements = json.loads(requirements_file.read_text())
                    frontend_metadata = requirements.get("metadata", {})

                    # Read existing task_metadata or create new
                    if task_metadata_file.exists():
                        task_metadata = json.loads(task_metadata_file.read_text())
                    else:
                        task_metadata = {}

                    # Sync requireReviewBeforeCoding from frontend to backend
                    if "requireReviewBeforeCoding" in frontend_metadata:
                        task_metadata["requireReviewBeforeCoding"] = frontend_metadata["requireReviewBeforeCoding"]

                    # Save updated task_metadata.json
                    task_metadata_file.write_text(json.dumps(task_metadata, indent=2))

                    require_review = task_metadata.get("requireReviewBeforeCoding", False)
                except (json.JSONDecodeError, OSError) as e:
                    logger.warning(f"[AgentService] Could not sync metadata for {task_id}: {e}")
            elif task_metadata_file.exists():
                try:
                    import json
                    task_metadata = json.loads(task_metadata_file.read_text())
                    require_review = task_metadata.get("requireReviewBeforeCoding", False)
                    # Note: Quick Mode no longer forces review - respect requireReviewBeforeCoding setting
                except (json.JSONDecodeError, OSError):
                    pass

            # Add --force flag if:
            # 1. Review is not required OR
            # 2. Plan was manually approved (force=True from approve_plan endpoint)
            if not require_review or force:
                cmd.append("--force")  # Bypass approval check for headless execution
                if force:
                    logger.info(f"[AgentService] Using --force for {task_id} (plan manually approved)")
            else:
                logger.info(f"[AgentService] Human review before coding enabled for task {task_id} - not using --force")

        if base_branch:
            cmd.extend(["--base-branch", base_branch])

        # Skip QA for quick mode (simple tasks) - coder_quick.md validates inline
        if mode == "quick":
            cmd.append("--skip-qa")
            logger.info(f"[AgentService] Skipping QA for quick mode task {task_id}")

        # Set environment
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        # Run Claude in non-interactive mode - bypass permission prompts
        env["CLAUDE_CODE_ENTRYPOINT"] = "cli"  # Signal non-interactive mode
        env["CI"] = "true"  # Many CLI tools use this to detect non-interactive mode

        # Quick Mode: Use simplified prompts (~70% fewer tokens)
        if mode == "quick":
            env["QUICK_MODE"] = "true"
            logger.info(f"[AgentService] Quick Mode enabled for task {task_id}")

        # Load backend .env file for graphiti and other settings
        backend_env_file = self.backend_path / ".env"
        if backend_env_file.exists():
            try:
                with open(backend_env_file) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip()
                            # Don't override existing env vars
                            if key not in env:
                                env[key] = value
                logger.info(f"[AgentService] Loaded backend .env from {backend_env_file}")
            except Exception as e:
                logger.warning(f"[AgentService] Failed to load backend .env: {e}")

        # Load project .magestic-ai/.env for project-level settings (USE_CLAUDE_MD, etc.)
        project_env_file = project_path / ".magestic-ai" / ".env"
        if project_env_file.exists():
            try:
                with open(project_env_file) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip()
                            if key not in env:
                                env[key] = value
                logger.info(f"[AgentService] Loaded project .env for task execution")
            except Exception as e:
                logger.warning(f"[AgentService] Failed to load project .env: {e}")

        # Get OAuth token with profile tracking
        token, profile_id, profile_name = self._resolve_claude_token()
        if token:
            env["CLAUDE_CODE_OAUTH_TOKEN"] = token
            logger.info(f"[AgentService] Using Claude profile: {profile_name} ({profile_id})")
            # Store for potential retry
            self._task_profiles[task_id] = {
                "profileId": profile_id,
                "profileName": profile_name,
                "attempt": 1
            }
        else:
            logger.warning("[AgentService] No Claude OAuth token available")

        logger.info(f"[AgentService] Command: {' '.join(cmd)}")

        # Start subprocess with a pseudo-TTY to prevent "Stream closed" errors
        # Claude Code CLI expects a TTY for permission handling
        import pty

        master_fd, slave_fd = pty.openpty()

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=slave_fd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(project_path),
            env=env,
        )

        # Close slave fd in parent process
        os.close(slave_fd)

        self.running_tasks[task_id] = proc

        # Initialize tracking for sequence numbers and start time
        self._task_sequence_numbers[task_id] = 0
        self._task_start_times[task_id] = datetime.now().isoformat()
        # Store spec directory for reading implementation plans during progress updates
        self._spec_dirs[task_id] = spec_dir

        # Create TaskLogWriter for detailed phase logs
        # Write to worktree spec dir (will be synced to main spec dir)
        worktree_spec_dir = project_path / ".magestic-ai" / "worktrees" / "tasks" / spec_id / ".magestic-ai" / "specs" / spec_id
        worktree_spec_dir.mkdir(parents=True, exist_ok=True)
        log_writer = TaskLogWriter(worktree_spec_dir)

        # Also write to main spec dir for immediate visibility
        main_spec_dir = project_path / ".magestic-ai" / "specs" / spec_id
        main_spec_dir.mkdir(parents=True, exist_ok=True)
        main_log_writer = TaskLogWriter(main_spec_dir)

        # Store log writers for cleanup
        self._task_log_writers[task_id] = (log_writer, main_log_writer)

        # Emit initial progress (100% within planning phase → 20% overall)
        await self._emit_progress(TaskProgress(
            task_id=task_id,
            phase=TaskPhase.PLANNING,
            message="Starting task execution...",
            percentage=100,
        ))

        # Initialize planning phase in logs
        log_writer.set_phase_status(spec_id, TaskPhase.PLANNING, "active")
        main_log_writer.set_phase_status(spec_id, TaskPhase.PLANNING, "active")

        # Start output processing in background with log writers
        asyncio.create_task(self._process_output(
            task_id, proc.stdout, is_stderr=False,
            log_writer=log_writer, spec_id=spec_id
        ))
        asyncio.create_task(self._process_output(task_id, proc.stderr, is_stderr=True))

        # Start process monitor to clean up when finished (with file syncing and failover support)
        asyncio.create_task(self._monitor_process(task_id, proc, project_path, spec_id, cmd, env))

        return proc

    async def stop_task(self, task_id: str) -> bool:
        """Stop a running task."""
        import logging
        logger = logging.getLogger(__name__)
        if task_id not in self.running_tasks:
            logger.info(f"[AgentService] Task {task_id} not in running_tasks (already stopped or never started)")
            return False

        proc = self.running_tasks[task_id]
        proc.terminate()

        try:
            await asyncio.wait_for(proc.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()

        # Use pop with default to handle race condition where _monitor_process
        # might have already removed the task
        self.running_tasks.pop(task_id, None)
        self._task_sequence_numbers.pop(task_id, None)
        self._task_start_times.pop(task_id, None)
        self._task_subtask_states.pop(task_id, None)
        self._spec_dirs.pop(task_id, None)

        await self._emit_progress(TaskProgress(
            task_id=task_id,
            phase=TaskPhase.FAILED,
            message="Task stopped by user",
        ))

        return True

    async def wait_for_task(self, task_id: str) -> int:
        """Wait for a task to complete and return exit code."""
        if task_id not in self.running_tasks:
            raise ValueError(f"Task {task_id} is not running")

        proc = self.running_tasks[task_id]
        return_code = await proc.wait()

        del self.running_tasks[task_id]
        self._task_sequence_numbers.pop(task_id, None)
        self._task_start_times.pop(task_id, None)
        self._task_subtask_states.pop(task_id, None)
        self._spec_dirs.pop(task_id, None)

        if return_code == 0:
            await self._emit_progress(TaskProgress(
                task_id=task_id,
                phase=TaskPhase.COMPLETED,
                message="Task completed successfully",
            ))
        else:
            await self._emit_progress(TaskProgress(
                task_id=task_id,
                phase=TaskPhase.FAILED,
                message=f"Task failed with exit code {return_code}",
            ))

        return return_code

    def is_running(self, task_id: str) -> bool:
        """Check if a task is currently running."""
        return task_id in self.running_tasks

    def get_running_tasks(self) -> list[str]:
        """Get list of running task IDs."""
        return list(self.running_tasks.keys())


# Global service instance
_agent_service: AgentService | None = None


def get_agent_service() -> AgentService:
    """Get the global agent service instance."""
    global _agent_service
    if _agent_service is None:
        _agent_service = AgentService()
    return _agent_service
