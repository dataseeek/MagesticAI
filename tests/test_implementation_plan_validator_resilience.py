#!/usr/bin/env python3
"""
Regression tests for ImplementationPlanValidator schema-drift resilience.

When a (typically smaller) LLM emits an implementation_plan.json with the
wrong shape — e.g. ``"phases"`` as a dict-of-dicts instead of a list of
phase objects — the validator must return a structured ValidationResult
with errors rather than raising an unhandled AttributeError that crashes
the entire spec pipeline.

These tests pin the defensive behaviour so a regression would be caught
immediately.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make apps/backend importable
_BACKEND = Path(__file__).parent.parent / "apps" / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from spec.validate_pkg.validators.implementation_plan_validator import (  # noqa: E402
    ImplementationPlanValidator,
)


def _validate(plan: dict, tmp_path: Path):
    """Write ``plan`` to a temp spec dir and run the validator against it."""
    import json
    plan_file = tmp_path / "implementation_plan.json"
    plan_file.write_text(json.dumps(plan))
    v = ImplementationPlanValidator(tmp_path)
    return v.validate()


class TestSchemaDriftResilience:
    """The validator must NEVER raise on malformed structured input."""

    def test_phases_as_dict_returns_error(self, tmp_path: Path):
        """qwen3-produced shape: phases is a dict-of-dicts, not a list."""
        plan = {
            "feature": "Hello World",
            "workflow_type": "feature",
            "phases": {
                "Implementation": {
                    "all": [
                        {"subtask_id": "test_implementation", "status": "completed"},
                    ],
                },
            },
        }
        # Must not raise
        result = _validate(plan, tmp_path)
        assert result.valid is False
        assert any(
            "phases" in err and "list" in err for err in result.errors
        ), f"Expected an error about 'phases' shape, got: {result.errors}"

    def test_phase_as_string_in_list_returns_error(self, tmp_path: Path):
        """phases is a list, but contains a string instead of an object."""
        plan = {
            "feature": "Hello World",
            "workflow_type": "feature",
            "phases": ["Implementation", "Testing"],
        }
        result = _validate(plan, tmp_path)
        assert result.valid is False
        assert any(
            "expected" in err.lower() and "object" in err.lower()
            for err in result.errors
        ), f"Expected an error about phase shape, got: {result.errors}"

    def test_phases_missing_entirely(self, tmp_path: Path):
        plan = {"feature": "Hello", "workflow_type": "feature"}
        result = _validate(plan, tmp_path)
        assert result.valid is False
        # Pre-existing "No phases defined" error path still triggers
        assert any("phases" in err.lower() for err in result.errors)

    def test_phases_as_none_returns_error(self, tmp_path: Path):
        plan = {
            "feature": "Hello",
            "workflow_type": "feature",
            "phases": None,
        }
        # Must not raise
        result = _validate(plan, tmp_path)
        assert result.valid is False

    def test_phases_as_int_returns_error(self, tmp_path: Path):
        plan = {
            "feature": "Hello",
            "workflow_type": "feature",
            "phases": 3,  # weird, but possible from a creative LLM
        }
        result = _validate(plan, tmp_path)
        assert result.valid is False

    def test_valid_plan_still_validates(self, tmp_path: Path):
        """Sanity check — a well-formed plan still passes."""
        plan = {
            "feature": "Hello World",
            "workflow_type": "feature",
            "phases": [
                {
                    "phase": 1,
                    "name": "Implementation",
                    "subtasks": [
                        {
                            "id": "script_creation",
                            "description": "Create hello_world.py",
                            "status": "pending",
                        },
                    ],
                },
            ],
        }
        result = _validate(plan, tmp_path)
        # If the schema requires other fields we don't care about here, we at
        # least confirm we didn't crash AND the phases-shape errors are gone.
        phase_shape_errors = [
            e for e in result.errors
            if "must be a JSON list" in e or "expected an object" in e
        ]
        assert phase_shape_errors == [], (
            f"Schema-drift defensive checks shouldn't fire on a valid plan: "
            f"{phase_shape_errors}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
