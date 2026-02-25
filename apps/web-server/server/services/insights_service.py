"""
Insights AI Chat Service.

Provides AI-powered chat for codebase exploration using Claude Code CLI.
Streams responses via WebSocket and persists sessions to disk.
"""

import asyncio
import json
import os
import shutil
import subprocess
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from ..config import get_settings
from ..websockets.events import broadcast_event


@dataclass
class InsightsMessage:
    """A single chat message."""
    id: str
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: str
    suggested_task: dict | None = None
    tools_used: list | None = None


@dataclass
class InsightsSession:
    """A chat session with history."""
    id: str
    project_id: str
    title: str
    messages: list[InsightsMessage] = field(default_factory=list)
    model_config: dict | None = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


class InsightsService:
    """Service for AI-powered insights chat."""

    def __init__(self):
        self.settings = get_settings()
        self._running_chats: dict[str, asyncio.subprocess.Process] = {}
        self._sessions: dict[str, InsightsSession] = {}  # Cache
        self._claude_path: str | None = None  # Cached CLI path

    def _resolve_claude_path(self) -> str:
        """Resolve the full path to the claude CLI."""
        if self._claude_path:
            return self._claude_path

        # 1) Direct lookup (works if PATH includes ~/.local/bin)
        path = shutil.which("claude")
        if path:
            self._claude_path = path
            return path

        # 2) Login shell fallback (picks up fnm/npm global PATH)
        try:
            result = subprocess.run(
                ["bash", "-l", "-c", "which claude"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                self._claude_path = result.stdout.strip()
                return self._claude_path
        except (subprocess.SubprocessError, OSError):
            pass

        # 3) Common install locations
        home = Path.home()
        for candidate in [
            home / ".local" / "bin" / "claude",
            Path("/usr/local/bin/claude"),
        ]:
            if candidate.exists():
                self._claude_path = str(candidate)
                return self._claude_path

        # Last resort: bare name (will fail if not in PATH)
        return "claude"

    def _resolve_claude_token(self) -> tuple[str | None, str | None, str | None]:
        """Resolve Claude OAuth token with profile-aware fallback."""
        # 1) Environment override
        env_token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")
        if env_token:
            return (env_token, "env-override", "Environment Override")

        # 2) Active profile from profiles file
        profiles_file = Path(self.settings.PROJECTS_DATA_DIR) / "claude-profiles.json"
        from ..paths import get_data_file
        legacy_profiles_file = get_data_file("claude-profiles.json")
        if not profiles_file.exists() and legacy_profiles_file.exists():
            profiles_file = legacy_profiles_file

        if profiles_file.exists():
            try:
                data = json.loads(profiles_file.read_text())
                profiles = data.get("profiles", [])
                active_id = data.get("activeProfileId")

                usable = [
                    p for p in profiles
                    if p.get("oauthToken") or p.get("token")
                ]

                for profile in usable:
                    if profile.get("id") == active_id:
                        token = profile.get("oauthToken") or profile.get("token")
                        return (token, profile.get("id"), profile.get("name", "Active Profile"))

                if usable:
                    profile = usable[0]
                    token = profile.get("oauthToken") or profile.get("token")
                    return (token, profile.get("id"), profile.get("name", "Default Profile"))
            except (json.JSONDecodeError, OSError):
                pass

        # 3) Fallback to ~/.claude/oauth_token
        token_file = Path.home() / ".claude" / "oauth_token"
        if token_file.exists():
            token = token_file.read_text().strip()
            if token:
                return (token, "static-fallback", "Static Token")

        return (None, None, None)

    def _get_sessions_dir(self, project_path: Path) -> Path:
        """Get the directory for storing insight sessions."""
        sessions_dir = project_path / ".magestic-ai" / "insights"
        sessions_dir.mkdir(parents=True, exist_ok=True)
        return sessions_dir

    def _get_session_file(self, project_path: Path, session_id: str) -> Path:
        """Get the file path for a specific session."""
        return self._get_sessions_dir(project_path) / f"{session_id}.json"

    def _get_current_session_file(self, project_path: Path) -> Path:
        """Get the file that tracks the current active session."""
        return self._get_sessions_dir(project_path) / "current_session.txt"

    def _save_session(self, project_path: Path, session: InsightsSession) -> None:
        """Save a session to disk."""
        session.updated_at = datetime.now().isoformat()
        session_file = self._get_session_file(project_path, session.id)

        # Convert to dict for JSON serialization
        data = {
            "id": session.id,
            "projectId": session.project_id,
            "title": session.title,
            "messages": [
                {
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp,
                    "suggestedTask": msg.suggested_task,
                    "toolsUsed": msg.tools_used,
                }
                for msg in session.messages
            ],
            "modelConfig": session.model_config,
            "createdAt": session.created_at,
            "updatedAt": session.updated_at,
        }

        with open(session_file, 'w') as f:
            json.dump(data, f, indent=2)

        # Update cache
        self._sessions[session.id] = session

    def _load_session(self, project_path: Path, session_id: str) -> InsightsSession | None:
        """Load a session from disk."""
        # Check cache first
        if session_id in self._sessions:
            return self._sessions[session_id]

        session_file = self._get_session_file(project_path, session_id)
        if not session_file.exists():
            return None

        try:
            with open(session_file) as f:
                data = json.load(f)

            session = InsightsSession(
                id=data["id"],
                project_id=data.get("projectId", ""),
                title=data.get("title", "New Session"),
                messages=[
                    InsightsMessage(
                        id=msg["id"],
                        role=msg["role"],
                        content=msg["content"],
                        timestamp=msg["timestamp"],
                        suggested_task=msg.get("suggestedTask"),
                        tools_used=msg.get("toolsUsed"),
                    )
                    for msg in data.get("messages", [])
                ],
                model_config=data.get("modelConfig"),
                created_at=data.get("createdAt", datetime.now().isoformat()),
                updated_at=data.get("updatedAt", datetime.now().isoformat()),
            )

            # Update cache
            self._sessions[session_id] = session
            return session
        except (json.JSONDecodeError, KeyError) as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to load session {session_id}: {e}")
            return None

    def get_current_session(self, project_path: Path, project_id: str) -> InsightsSession:
        """Get or create the current session for a project."""
        current_file = self._get_current_session_file(project_path)

        # Try to load current session
        if current_file.exists():
            session_id = current_file.read_text().strip()
            session = self._load_session(project_path, session_id)
            if session:
                return session

        # Create new session
        return self.create_session(project_path, project_id)

    def create_session(self, project_path: Path, project_id: str) -> InsightsSession:
        """Create a new session."""
        session = InsightsSession(
            id=str(uuid.uuid4()),
            project_id=project_id,
            title="New Session",
        )

        self._save_session(project_path, session)

        # Set as current session
        current_file = self._get_current_session_file(project_path)
        current_file.write_text(session.id)

        return session

    def switch_session(self, project_path: Path, session_id: str) -> InsightsSession | None:
        """Switch to a different session."""
        session = self._load_session(project_path, session_id)
        if session:
            current_file = self._get_current_session_file(project_path)
            current_file.write_text(session_id)
        return session

    def list_sessions(self, project_path: Path) -> list[dict]:
        """List all sessions for a project."""
        sessions_dir = self._get_sessions_dir(project_path)
        sessions = []

        for session_file in sessions_dir.glob("*.json"):
            if session_file.name == "current_session.txt":
                continue
            try:
                with open(session_file) as f:
                    data = json.load(f)
                sessions.append({
                    "id": data["id"],
                    "title": data.get("title", "Untitled"),
                    "messageCount": len(data.get("messages", [])),
                    "createdAt": data.get("createdAt"),
                    "updatedAt": data.get("updatedAt"),
                })
            except (json.JSONDecodeError, KeyError):
                continue

        # Sort by updated_at descending
        sessions.sort(key=lambda x: x.get("updatedAt", ""), reverse=True)
        return sessions

    def delete_session(self, project_path: Path, session_id: str) -> bool:
        """Delete a session."""
        session_file = self._get_session_file(project_path, session_id)
        if session_file.exists():
            session_file.unlink()

            # Remove from cache
            if session_id in self._sessions:
                del self._sessions[session_id]

            # If this was the current session, clear it
            current_file = self._get_current_session_file(project_path)
            if current_file.exists() and current_file.read_text().strip() == session_id:
                current_file.unlink()

            return True
        return False

    def rename_session(self, project_path: Path, session_id: str, new_title: str) -> bool:
        """Rename a session."""
        session = self._load_session(project_path, session_id)
        if session:
            session.title = new_title
            self._save_session(project_path, session)
            return True
        return False

    def update_model_config(self, project_path: Path, session_id: str, model_config: dict) -> bool:
        """Update model config for a session."""
        session = self._load_session(project_path, session_id)
        if session:
            session.model_config = model_config
            self._save_session(project_path, session)
            return True
        return False

    async def send_message(
        self,
        project_path: Path,
        project_id: str,
        message: str,
        model_config: dict | None = None,
    ) -> None:
        """Send a message and stream the response."""
        import logging
        logger = logging.getLogger(__name__)

        # Get current session
        session = self.get_current_session(project_path, project_id)

        # Add user message
        user_msg = InsightsMessage(
            id=f"msg-{uuid.uuid4().hex[:8]}",
            role="user",
            content=message,
            timestamp=datetime.now().isoformat(),
        )
        session.messages.append(user_msg)

        # Auto-generate title from first message if still "New Session"
        if session.title == "New Session" and len(session.messages) == 1:
            # Take first 50 chars of message as title
            session.title = message[:50] + ("..." if len(message) > 50 else "")

        self._save_session(project_path, session)

        # Build Claude Code CLI command
        # Use --print flag for non-interactive output
        # Note: --verbose is required when using --print with --output-format stream-json
        claude_bin = self._resolve_claude_path()
        cmd = [
            claude_bin,
            "--print",  # Non-interactive, print output
            "--verbose",  # Required for stream-json with --print
            "--output-format", "stream-json",  # Stream JSON for tool visibility
        ]

        # Apply model and thinking level from agent profile config
        if model_config:
            model_value = model_config.get("model")
            if model_value:
                # CLI accepts shorthand: opus, sonnet, haiku
                cmd.extend(["--model", model_value])

            thinking_level = model_config.get("thinkingLevel")
            if thinking_level and thinking_level != "none":
                # Map thinking levels to CLI --effort flag
                effort_map = {
                    "low": "low",
                    "medium": "medium",
                    "high": "high",
                    "ultrathink": "high",
                }
                effort = effort_map.get(thinking_level)
                if effort:
                    cmd.extend(["--effort", effort])

        # Add the message as the prompt
        cmd.append(message)

        # Set environment
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        # Remove CLAUDECODE to avoid "nested session" rejection
        env.pop("CLAUDECODE", None)

        # Get OAuth token with active profile preference
        token, profile_id, profile_name = self._resolve_claude_token()
        if token:
            env["CLAUDE_CODE_OAUTH_TOKEN"] = token
            logger.info(
                f"[InsightsService] Using Claude profile: {profile_name} ({profile_id})"
            )
        else:
            logger.warning("[InsightsService] No Claude OAuth token available")

        logger.info(f"[InsightsService] Starting Claude CLI: {' '.join(cmd[:5])}...")

        try:
            # Emit thinking status
            await broadcast_event("insights:chunk", {
                "projectId": project_id,
                "type": "text",
                "content": "",
            })

            # Start subprocess
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(project_path),
                env=env,
            )

            self._running_chats[project_id] = proc

            # Process streaming output
            accumulated_content = ""
            tools_used = []

            async for line_bytes in proc.stdout:
                line = line_bytes.decode("utf-8", errors="replace").rstrip()

                if not line:
                    continue

                # Try to parse as JSON (stream-json format)
                if line.startswith("{"):
                    try:
                        data = json.loads(line)

                        # Handle different event types
                        event_type = data.get("type", "")

                        if event_type == "assistant":
                            # Text content
                            content = data.get("message", {}).get("content", "")
                            if isinstance(content, list):
                                for block in content:
                                    if block.get("type") == "text":
                                        text = block.get("text", "")
                                        accumulated_content += text
                                        await broadcast_event("insights:chunk", {
                                            "projectId": project_id,
                                            "type": "text",
                                            "content": text,
                                        })
                            elif isinstance(content, str):
                                accumulated_content += content
                                await broadcast_event("insights:chunk", {
                                    "projectId": project_id,
                                    "type": "text",
                                    "content": content,
                                })

                        elif event_type == "content_block_delta":
                            # Streaming text delta
                            delta = data.get("delta", {})
                            if delta.get("type") == "text_delta":
                                text = delta.get("text", "")
                                accumulated_content += text
                                await broadcast_event("insights:chunk", {
                                    "projectId": project_id,
                                    "type": "text",
                                    "content": text,
                                })

                        elif event_type == "tool_use":
                            # Tool invocation
                            tool_name = data.get("name", data.get("tool", "Unknown"))
                            tool_input = data.get("input", "")
                            if isinstance(tool_input, dict):
                                # Extract relevant input (file_path, pattern, etc.)
                                tool_input = tool_input.get("file_path") or tool_input.get("pattern") or str(tool_input)[:100]

                            tools_used.append({
                                "name": tool_name,
                                "input": str(tool_input)[:200],
                                "timestamp": datetime.now().isoformat(),
                            })

                            await broadcast_event("insights:chunk", {
                                "projectId": project_id,
                                "type": "tool_start",
                                "tool": {"name": tool_name, "input": str(tool_input)[:200]},
                            })

                        elif event_type == "tool_result":
                            await broadcast_event("insights:chunk", {
                                "projectId": project_id,
                                "type": "tool_end",
                            })

                        elif event_type == "result":
                            # Final result
                            result = data.get("result", "")
                            if result and result != accumulated_content:
                                accumulated_content = result
                                await broadcast_event("insights:chunk", {
                                    "projectId": project_id,
                                    "type": "text",
                                    "content": result,
                                })

                        continue
                    except json.JSONDecodeError:
                        pass

                # Plain text output (non-JSON)
                accumulated_content += line + "\n"
                await broadcast_event("insights:chunk", {
                    "projectId": project_id,
                    "type": "text",
                    "content": line + "\n",
                })

            # Wait for process to complete
            await proc.wait()

            # Check stderr for errors
            stderr_output = await proc.stderr.read()
            stderr_text = ""
            if stderr_output:
                stderr_text = stderr_output.decode("utf-8", errors="replace").strip()
                logger.warning(f"[InsightsService] Claude stderr: {stderr_text}")

            # If process failed and no content was produced, broadcast the error
            if proc.returncode != 0 and not accumulated_content.strip():
                error_msg = stderr_text or f"Claude CLI exited with code {proc.returncode}"
                logger.error(f"[InsightsService] Claude CLI failed: {error_msg}")
                await broadcast_event("insights:chunk", {
                    "projectId": project_id,
                    "type": "error",
                    "error": error_msg,
                })
                return

            # Save assistant message
            if accumulated_content.strip():
                assistant_msg = InsightsMessage(
                    id=f"msg-{uuid.uuid4().hex[:8]}",
                    role="assistant",
                    content=accumulated_content.strip(),
                    timestamp=datetime.now().isoformat(),
                    tools_used=tools_used if tools_used else None,
                )
                session.messages.append(assistant_msg)
                self._save_session(project_path, session)

            # Emit done
            await broadcast_event("insights:chunk", {
                "projectId": project_id,
                "type": "done",
            })

        except Exception as e:
            logger.error(f"[InsightsService] Error: {e}", exc_info=True)
            await broadcast_event("insights:chunk", {
                "projectId": project_id,
                "type": "error",
                "error": str(e),
            })
        finally:
            if project_id in self._running_chats:
                del self._running_chats[project_id]

    def clear_session(self, project_path: Path, project_id: str) -> InsightsSession:
        """Clear the current session and create a new one."""
        current_file = self._get_current_session_file(project_path)

        # Delete current session if exists
        if current_file.exists():
            session_id = current_file.read_text().strip()
            self.delete_session(project_path, session_id)

        # Create new session
        return self.create_session(project_path, project_id)


# Global service instance
_insights_service: InsightsService | None = None


def get_insights_service() -> InsightsService:
    """Get the global insights service instance."""
    global _insights_service
    if _insights_service is None:
        _insights_service = InsightsService()
    return _insights_service
