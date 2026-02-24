"""
Quick Mode Optimizations
========================

Performance improvements for quick/simple spec creation:
1. Template-based instant generation for common patterns
2. Reduced thinking budgets
3. Parallel operations
4. Smart caching
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import TypedDict


class QuickSpecTemplate(TypedDict):
    """Template for quick spec generation."""

    pattern: str  # Regex pattern to match task description
    spec_template: str  # Template for spec.md
    subtask_template: str  # Template for subtask description


# Common task patterns that can be handled with templates
QUICK_TEMPLATES: list[QuickSpecTemplate] = [
    {
        "pattern": r"(?i)(fix|correct|update)\s+(typo|spelling|text|wording)",
        "spec_template": """# Quick Spec: {task_title}

## Task
{task_description}

## Files to Modify
- {file_path} - Correct text/typo

## Change Details
Update the text as described in the task.

## Verification
- [ ] Text displays correctly
- [ ] No new typos introduced
""",
        "subtask_template": "Update text in {file_path} as described",
    },
    {
        "pattern": r"(?i)(change|update|modify).*(color|style|css|background)",
        "spec_template": """# Quick Spec: {task_title}

## Task
{task_description}

## Files to Modify
- {file_path} - Update styling

## Change Details
Modify the CSS/styling as described in the task.

## Verification
- [ ] Visual appearance matches requirements
- [ ] No style regressions in other components
""",
        "subtask_template": "Update styling in {file_path}",
    },
    {
        "pattern": r"(?i)(add|remove|update).*(button|link|icon|element)",
        "spec_template": """# Quick Spec: {task_title}

## Task
{task_description}

## Files to Modify
- {file_path} - Add/remove/update UI element

## Change Details
{task_description}

## Verification
- [ ] Element appears/functions correctly
- [ ] No layout issues
- [ ] Accessibility maintained
""",
        "subtask_template": "Modify UI element in {file_path}",
    },
]


def match_quick_template(task_description: str) -> QuickSpecTemplate | None:
    """Try to match task description to a quick template.

    Args:
        task_description: The task description

    Returns:
        Matching template or None if no match
    """
    for template in QUICK_TEMPLATES:
        if re.search(template["pattern"], task_description):
            return template
    return None


def extract_file_path_from_task(task_description: str) -> str:
    """Try to extract a file path from task description.

    Args:
        task_description: The task description

    Returns:
        Extracted file path or placeholder
    """
    # Look for common file path patterns
    patterns = [
        r"`([^`]+\.(tsx?|jsx?|py|css|html|vue|svelte))`",  # Backtick quoted
        r"in\s+([^\s]+\.(tsx?|jsx?|py|css|html|vue|svelte))",  # "in filename"
        r"file[:\s]+([^\s]+\.(tsx?|jsx?|py|css|html|vue|svelte))",  # "file: filename"
    ]

    for pattern in patterns:
        match = re.search(pattern, task_description, re.IGNORECASE)
        if match:
            return match.group(1)

    return "[file-to-modify]"


def generate_task_title(task_description: str, max_length: int = 60) -> str:
    """Generate a clean title from task description.

    Args:
        task_description: The task description
        max_length: Maximum title length

    Returns:
        Clean title string
    """
    # Take first sentence or first line
    first_sentence = task_description.split(".")[0].split("\n")[0].strip()

    # Clean up
    title = first_sentence.replace("\n", " ").strip()

    # Truncate if needed
    if len(title) > max_length:
        title = title[:max_length - 3] + "..."

    return title


def create_quick_spec_from_template(
    spec_dir: Path,
    task_description: str,
    template: QuickSpecTemplate,
) -> tuple[Path, Path]:
    """Create spec.md and implementation_plan.json from template.

    Args:
        spec_dir: Spec directory path
        task_description: Task description
        template: The template to use

    Returns:
        Tuple of (spec_file_path, plan_file_path)
    """
    spec_dir = Path(spec_dir)
    spec_dir.mkdir(parents=True, exist_ok=True)

    # Extract info from task
    file_path = extract_file_path_from_task(task_description)
    task_title = generate_task_title(task_description)

    # Generate spec.md from template
    spec_content = template["spec_template"].format(
        task_title=task_title,
        task_description=task_description,
        file_path=file_path,
    )

    spec_file = spec_dir / "spec.md"
    spec_file.write_text(spec_content, encoding="utf-8")

    # Generate implementation_plan.json
    plan = {
        "spec_name": spec_dir.name,
        "workflow_type": "simple",
        "total_phases": 1,
        "recommended_workers": 1,
        "phases": [
            {
                "phase": 1,
                "name": "Implementation",
                "description": task_description,
                "depends_on": [],
                "subtasks": [
                    {
                        "id": "subtask-1-1",
                        "description": template["subtask_template"].format(
                            file_path=file_path
                        ),
                        "service": "main",
                        "status": "pending",
                        "files_to_create": [],
                        "files_to_modify": [file_path] if file_path != "[file-to-modify]" else [],
                        "patterns_from": [],
                        "verification": {
                            "type": "manual",
                            "run": "Verify the change works as expected",
                        },
                    }
                ],
            }
        ],
        "metadata": {
            "created_at": datetime.now().isoformat(),
            "complexity": "simple",
            "estimated_sessions": 1,
            "generated_from": "template",
        },
    }

    plan_file = spec_dir / "implementation_plan.json"
    plan_file.write_text(json.dumps(plan, indent=2), encoding="utf-8")

    return spec_file, plan_file


def should_use_template_mode(task_description: str) -> bool:
    """Determine if template mode should be used.

    Args:
        task_description: The task description

    Returns:
        True if template mode is appropriate
    """
    # Very short tasks are good candidates
    if len(task_description) < 100:
        # Check if matches a template
        if match_quick_template(task_description):
            return True

    # Check for simple keyword indicators
    simple_indicators = [
        r"\bfix\s+typo\b",
        r"\bchange\s+color\b",
        r"\bupdate\s+text\b",
        r"\badd\s+button\b",
        r"\bremove\s+\w+\b",
    ]

    for indicator in simple_indicators:
        if re.search(indicator, task_description, re.IGNORECASE):
            return True

    return False


def get_optimized_thinking_budget(complexity: str) -> int:
    """Get optimized thinking budget for quick mode.

    Args:
        complexity: Complexity level (simple, standard, complex)

    Returns:
        Thinking budget in tokens
    """
    budgets = {
        "simple": 1000,  # Very low for quick tasks
        "standard": 5000,  # Standard budget
        "complex": 10000,  # Higher for complex tasks
    }
    return budgets.get(complexity, 5000)


# Export main functions
__all__ = [
    "match_quick_template",
    "create_quick_spec_from_template",
    "should_use_template_mode",
    "get_optimized_thinking_budget",
]
