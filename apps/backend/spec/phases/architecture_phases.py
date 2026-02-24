"""
Architecture Phase Implementation
=================================

Phase for generating technical architecture documents for complex projects (Level 3-4).
"""

import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from task_logger import LogEntryType, LogPhase

from .models import MAX_RETRIES, PhaseResult

if TYPE_CHECKING:
    pass


class ArchitecturePhaseMixin:
    """Mixin for architecture phase methods."""

    async def phase_architecture(self) -> PhaseResult:
        """
        Generate technical architecture document.

        This phase:
        1. Loads requirements.json and spec.md (if exists)
        2. Analyzes technical requirements
        3. Generates architecture.md with:
           - System overview
           - Database schema (ERD)
           - API design (OpenAPI)
           - Security considerations
           - Technical decision records (ADRs)
           - Mermaid diagrams
        4. Saves to spec directory

        Returns:
            PhaseResult with success status and generated files
        """
        architecture_file = self.spec_dir / "architecture.md"

        # Check if architecture already exists
        if architecture_file.exists():
            self.ui.print_status("architecture.md already exists", "success")
            self.task_logger.log(
                "Architecture document already available",
                LogEntryType.SUCCESS,
                LogPhase.PLANNING,
            )
            return PhaseResult("architecture", True, [str(architecture_file)], [], 0)

        # Load requirements for context
        requirements_file = self.spec_dir / "requirements.json"
        if not requirements_file.exists():
            self.ui.print_status(
                "requirements.json not found - architecture phase requires requirements",
                "error",
            )
            self.task_logger.log(
                "Architecture generation failed: missing requirements.json",
                LogEntryType.ERROR,
                LogPhase.PLANNING,
            )
            return PhaseResult(
                "architecture",
                False,
                [],
                ["requirements.json not found"],
                0
            )

        # Load spec.md if exists (may not exist yet in pipeline)
        spec_file = self.spec_dir / "spec.md"
        spec_content = ""
        if spec_file.exists():
            spec_content = spec_file.read_text()

        requirements_content = requirements_file.read_text()

        self.ui.print_status("Generating technical architecture...", "progress")
        self.task_logger.log(
            "Starting architecture generation (database, API, security, diagrams)...",
            LogEntryType.INFO,
            LogPhase.PLANNING,
        )

        # Build architecture prompt with context
        architecture_prompt = self._build_architecture_prompt(
            requirements_content, spec_content
        )

        # Run architecture agent
        success, response_text = await self.run_agent_fn(
            prompt_file="architecture",
            additional_context=architecture_prompt,
            phase_name="architecture",
        )

        if not success:
            self.ui.print_status("Architecture generation failed", "error")
            self.task_logger.log(
                "Architecture generation failed",
                LogEntryType.ERROR,
                LogPhase.PLANNING,
            )
            return PhaseResult("architecture", False, [], ["Agent execution failed"], 1)

        # Verify architecture.md was created
        if not architecture_file.exists():
            self.ui.print_status(
                "architecture.md not created by agent", "error"
            )
            self.task_logger.log(
                "Architecture document was not created",
                LogEntryType.ERROR,
                LogPhase.PLANNING,
            )
            return PhaseResult(
                "architecture",
                False,
                [],
                ["architecture.md not created"],
                1
            )

        self.ui.print_status("Architecture document created successfully", "success")
        self.task_logger.log(
            f"Architecture document generated: {architecture_file.name}",
            LogEntryType.SUCCESS,
            LogPhase.PLANNING,
        )

        return PhaseResult("architecture", True, [str(architecture_file)], [], 0)

    def _build_architecture_prompt(
        self, requirements_content: str, spec_content: str
    ) -> str:
        """
        Build the architecture generation prompt with context.

        Args:
            requirements_content: Content of requirements.json
            spec_content: Content of spec.md (if exists)

        Returns:
            Formatted prompt string
        """
        context_parts = []

        # Add requirements
        context_parts.append(
            "<requirements>\n" + requirements_content + "\n</requirements>"
        )

        # Add spec if available
        if spec_content:
            context_parts.append(
                "<specification>\n" + spec_content + "\n</specification>"
            )

        # Add project context if available
        project_context_file = self.project_dir / "project-context.md"
        if project_context_file.exists():
            context_parts.append(
                "<project_context>\n"
                + project_context_file.read_text()
                + "\n</project_context>"
            )

        return "\n\n".join(context_parts)
