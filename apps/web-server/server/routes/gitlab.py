"""
GitLab integration routes.

Handles GitLab OAuth, project management, issues, merge requests, and releases.
"""

import json
import subprocess
import sys
from pathlib import Path as FilePath

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter()


# ============================================
# Request/Response Models
# ============================================

class CreateProjectRequest(BaseModel):
    projectName: str
    description: str | None = None
    visibility: str = "private"
    groupId: int | None = None


class AddRemoteRequest(BaseModel):
    projectPath: str
    projectPathWithNamespace: str
    instanceUrl: str | None = None


class InvestigateRequest(BaseModel):
    selectedNoteIds: list[int] | None = None


class ImportIssuesRequest(BaseModel):
    issueIids: list[int]


class CreateMRRequest(BaseModel):
    sourceBranch: str
    targetBranch: str
    title: str
    description: str | None = None


class UpdateMRRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    labels: list[str] | None = None


class AssignMRRequest(BaseModel):
    userIds: list[int]


class PostNoteRequest(BaseModel):
    body: str


class PostReviewRequest(BaseModel):
    selectedFindingIds: list[str] | None = None
    reviewFindings: dict | None = None  # The review data from run_mr_review


class FollowupReviewRequest(BaseModel):
    additionalContext: str  # User's questions or additional context
    previousReview: dict | None = None  # Previous review findings for context
    focusAreas: list[str] | None = None  # Specific areas to focus on


class MergeRequest(BaseModel):
    mergeMethod: str | None = None


class CreateReleaseRequest(BaseModel):
    tagName: str
    releaseNotes: str
    ref: str | None = None


# ============================================
# GitLab CLI Helpers
# ============================================

def run_glab_command(args: list[str], cwd: str | None = None) -> dict:
    """Run a glab CLI command and return the result."""
    try:
        result = subprocess.run(
            ["glab"] + args,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=30
        )
        if result.returncode != 0:
            return {"success": False, "error": result.stderr.strip()}
        return {"success": True, "output": result.stdout.strip()}
    except FileNotFoundError:
        return {"success": False, "error": "GitLab CLI (glab) not installed"}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Command timed out"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================
# AI Analysis Helper
# ============================================

async def analyze_issue_with_ai(issue_data: dict, notes: list, project_path: str) -> dict:
    """
    Analyze a GitLab issue using AI.

    Args:
        issue_data: Issue data from GitLab API
        notes: List of notes/comments on the issue
        project_path: Path to the project directory

    Returns:
        Dictionary containing AI analysis results with keys:
        - summary: Brief summary of the issue
        - issue_type: Type of issue (bug, feature, documentation, etc.)
        - complexity: Complexity estimate (simple, standard, complex)
        - suggestions: List of suggested solutions or next steps
        - affected_areas: List of files/components that might need attention
        - risks: List of potential risks or concerns
    """
    # Add backend to Python path
    backend_path = FilePath(__file__).parent.parent.parent.parent / "backend"
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))

    try:
        from core.simple_client import create_simple_client
    except ImportError as e:
        raise RuntimeError(f"Failed to import simple_client: {e}")

    # Build analysis prompt
    prompt = _build_issue_analysis_prompt(issue_data, notes)

    # Create AI client for batch analysis
    try:
        client = create_simple_client(
            agent_type="batch_analysis",  # Read-only analysis agent
            model="claude-sonnet-4-20250514",  # Use Sonnet for better analysis
            cwd=FilePath(project_path),
            max_turns=1  # Single-turn analysis
        )
    except Exception as e:
        raise RuntimeError(f"Failed to create AI client: {e}")

    # Run AI analysis
    try:
        response = await client.send_message(prompt)

        # Extract analysis from response
        analysis = _parse_ai_analysis_response(response.content)
        return analysis

    except Exception as e:
        raise RuntimeError(f"AI analysis failed: {e}")


def _build_issue_analysis_prompt(issue_data: dict, notes: list) -> str:
    """Build the analysis prompt for the AI."""

    # Format notes for inclusion in prompt
    notes_text = ""
    if notes:
        notes_text = "\n\n## Comments/Notes\n\n"
        for note in notes[:10]:  # Limit to first 10 notes
            author = note.get("author", {}).get("username", "Unknown")
            body = note.get("body", "")
            created_at = note.get("created_at", "")
            notes_text += f"**{author}** ({created_at}):\n{body}\n\n"

    labels_text = ", ".join(issue_data.get("labels", [])) if issue_data.get("labels") else "None"

    prompt = f"""You are analyzing a GitLab issue to help understand what needs to be done and provide actionable insights.

## Issue Information

**Title:** {issue_data.get("title", "Unknown")}
**State:** {issue_data.get("state", "unknown")}
**Labels:** {labels_text}
**Author:** {issue_data.get("author", {}).get("username", "Unknown")}
**Created:** {issue_data.get("created_at", "Unknown")}
**Updated:** {issue_data.get("updated_at", "Unknown")}

## Description

{issue_data.get("description", "No description provided.")}
{notes_text}

## Your Task

Analyze this issue and provide structured insights in the following JSON format:

```json
{{
  "summary": "One paragraph summary of what this issue is about",
  "issue_type": "bug|feature|documentation|refactor|performance|security|other",
  "complexity": "simple|standard|complex",
  "suggestions": [
    "Specific, actionable suggestion for addressing this issue",
    "Another suggestion or next step"
  ],
  "affected_areas": [
    "File paths, components, or modules that might need changes",
    "API endpoints or functions that are relevant"
  ],
  "risks": [
    "Potential risk or concern to be aware of",
    "Another consideration"
  ]
}}
```

**Analysis Guidelines:**

1. **Issue Type Classification:**
   - bug: Something is broken or not working as expected
   - feature: New functionality request
   - documentation: Docs need to be added or updated
   - refactor: Code restructuring without behavior change
   - performance: Speed or efficiency improvements
   - security: Security vulnerability or concern
   - other: Doesn't fit other categories

2. **Complexity Levels:**
   - simple: Single file change, clear fix, < 1 hour
   - standard: Multiple files, moderate changes, 1-4 hours
   - complex: Architectural changes, many files, > 4 hours

3. **Suggestions:** Be specific and actionable. Focus on practical next steps.

4. **Affected Areas:** Identify specific files, components, or modules based on the issue description.

5. **Risks:** Consider backwards compatibility, breaking changes, edge cases, security implications.

Respond with ONLY the JSON object, no other text."""

    return prompt


def _parse_ai_analysis_response(response_content: str) -> dict:
    """Parse the AI's analysis response and extract structured data."""

    # Try to extract JSON from the response
    try:
        # Look for JSON code block
        if "```json" in response_content:
            start = response_content.find("```json") + 7
            end = response_content.find("```", start)
            json_text = response_content[start:end].strip()
        elif "```" in response_content:
            start = response_content.find("```") + 3
            end = response_content.find("```", start)
            json_text = response_content[start:end].strip()
        else:
            # Try to parse the whole response as JSON
            json_text = response_content.strip()

        analysis = json.loads(json_text)

        # Validate required fields
        required_fields = ["summary", "issue_type", "complexity", "suggestions", "affected_areas", "risks"]
        for field in required_fields:
            if field not in analysis:
                analysis[field] = [] if field in ["suggestions", "affected_areas", "risks"] else None

        return analysis

    except json.JSONDecodeError:
        # If JSON parsing fails, return a basic structure
        return {
            "summary": "AI analysis completed but response format was invalid.",
            "issue_type": "unknown",
            "complexity": "unknown",
            "suggestions": ["Review the issue manually for detailed analysis"],
            "affected_areas": [],
            "risks": [],
            "raw_response": response_content[:500]  # Include first 500 chars for debugging
        }


# ============================================
# MR Code Review AI Helper
# ============================================

async def analyze_mr_with_ai(mr_data: dict, diff_content: str, project_path: str) -> dict:
    """
    Analyze a GitLab merge request using AI for code review.

    Args:
        mr_data: MR data from GitLab API
        diff_content: Unified diff content showing all changes
        project_path: Path to the project directory

    Returns:
        Dictionary containing AI code review results with keys:
        - summary: Brief summary of the changes
        - review_status: Overall review status (approved, needs_work, blocked)
        - code_quality: Quality assessment (excellent, good, needs_improvement, poor)
        - findings: List of review findings with severity and details
        - security_concerns: List of security-related issues if any
        - performance_notes: Performance considerations
        - test_coverage: Assessment of test coverage for changes
    """
    # Add backend to Python path
    backend_path = FilePath(__file__).parent.parent.parent.parent / "backend"
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))

    try:
        from core.simple_client import create_simple_client
    except ImportError as e:
        raise RuntimeError(f"Failed to import simple_client: {e}")

    # Build review prompt
    prompt = _build_mr_review_prompt(mr_data, diff_content)

    # Create AI client for code review
    try:
        client = create_simple_client(
            agent_type="batch_analysis",  # Read-only analysis agent
            model="claude-sonnet-4-20250514",  # Use Sonnet for better code review
            cwd=FilePath(project_path),
            max_turns=1  # Single-turn analysis
        )
    except Exception as e:
        raise RuntimeError(f"Failed to create AI client: {e}")

    # Run AI code review
    try:
        response = await client.send_message(prompt)

        # Extract review from response
        review = _parse_mr_review_response(response.content)
        return review

    except Exception as e:
        raise RuntimeError(f"AI code review failed: {e}")


def _build_mr_review_prompt(mr_data: dict, diff_content: str) -> str:
    """Build the code review prompt for the AI."""

    # Truncate diff if too long (keep first 15000 chars)
    truncated = False
    if len(diff_content) > 15000:
        diff_content = diff_content[:15000]
        truncated = True

    labels_text = ", ".join(mr_data.get("labels", [])) if mr_data.get("labels") else "None"

    prompt = f"""You are conducting a thorough code review of a GitLab merge request. Provide constructive, actionable feedback.

## Merge Request Information

**Title:** {mr_data.get("title", "Unknown")}
**State:** {mr_data.get("state", "unknown")}
**Labels:** {labels_text}
**Author:** {mr_data.get("author", {}).get("username", "Unknown")}
**Source Branch:** {mr_data.get("source_branch", "unknown")} → **Target Branch:** {mr_data.get("target_branch", "unknown")}
**Created:** {mr_data.get("created_at", "Unknown")}

## Description

{mr_data.get("description", "No description provided.")}

## Code Changes

```diff
{diff_content}
```

{"**Note:** Diff truncated to first 15000 characters for analysis." if truncated else ""}

## Your Task

Perform a comprehensive code review and provide structured feedback in the following JSON format:

```json
{{
  "summary": "Brief summary of what this MR changes and your overall assessment",
  "review_status": "approved|needs_work|blocked",
  "code_quality": "excellent|good|needs_improvement|poor",
  "findings": [
    {{
      "severity": "critical|major|minor|suggestion",
      "category": "bug|security|performance|style|best_practice|documentation|testing|other",
      "file": "path/to/file.py",
      "line": 42,
      "message": "Clear description of the finding",
      "suggestion": "Specific recommendation for improvement"
    }}
  ],
  "security_concerns": [
    "Specific security issue or concern",
    "Another security consideration"
  ],
  "performance_notes": [
    "Performance consideration or optimization opportunity",
    "Another performance note"
  ],
  "test_coverage": "Assessment of whether changes are adequately tested"
}}
```

**Review Guidelines:**

1. **Review Status:**
   - approved: Changes look good, ready to merge
   - needs_work: Issues need to be addressed before merging
   - blocked: Critical issues that prevent merging

2. **Code Quality Levels:**
   - excellent: Well-structured, follows best practices, comprehensive tests
   - good: Solid implementation, minor improvements possible
   - needs_improvement: Several issues to address, refactoring recommended
   - poor: Major issues, significant rework needed

3. **Finding Severity:**
   - critical: Must fix - security vulnerabilities, bugs, data loss risks
   - major: Should fix - significant issues, poor design, missing error handling
   - minor: Nice to fix - style issues, minor improvements
   - suggestion: Optional improvements, optimizations, alternatives

4. **Finding Categories:**
   - bug: Logic errors, edge cases not handled, potential crashes
   - security: Authentication, authorization, injection, data exposure
   - performance: Inefficient algorithms, N+1 queries, memory leaks
   - style: Code formatting, naming conventions, organization
   - best_practice: Design patterns, SOLID principles, maintainability
   - documentation: Missing docs, unclear comments
   - testing: Missing tests, inadequate coverage
   - other: Doesn't fit above categories

5. **Focus Areas:**
   - Correctness: Does the code do what it's supposed to do?
   - Security: Are there security vulnerabilities?
   - Performance: Are there efficiency concerns?
   - Maintainability: Is the code clear and well-organized?
   - Testing: Are changes adequately tested?
   - Error Handling: Are errors properly caught and handled?

Respond with ONLY the JSON object, no other text."""

    return prompt


def _build_followup_review_prompt(mr_data: dict, diff_content: str, additional_context: str, previous_review: dict | None = None, focus_areas: list[str] | None = None) -> str:
    """Build a followup code review prompt with additional user context."""

    # Truncate diff if too long (keep first 15000 chars)
    truncated = False
    if len(diff_content) > 15000:
        diff_content = diff_content[:15000]
        truncated = True

    labels_text = ", ".join(mr_data.get("labels", [])) if mr_data.get("labels") else "None"

    # Build previous review context if available
    previous_context = ""
    if previous_review:
        previous_context = f"""
## Previous Review Context

**Previous Summary:** {previous_review.get("summary", "N/A")}
**Previous Status:** {previous_review.get("review_status", "N/A")}
**Previous Code Quality:** {previous_review.get("code_quality", "N/A")}

**Previous Findings ({len(previous_review.get("findings", []))}):**
"""
        for i, finding in enumerate(previous_review.get("findings", [])[:5], 1):  # Show first 5
            previous_context += f"""
{i}. **{finding.get("severity", "unknown")}** - {finding.get("category", "unknown")}
   File: {finding.get("file", "unknown")} (line {finding.get("line", "?")})
   Message: {finding.get("message", "N/A")}
"""
        if len(previous_review.get("findings", [])) > 5:
            previous_context += f"\n(+ {len(previous_review.get('findings', [])) - 5} more findings)\n"

    # Build focus areas section if provided
    focus_text = ""
    if focus_areas and len(focus_areas) > 0:
        focus_text = f"""
## Specific Focus Areas Requested

The user has requested you focus on the following areas:
{chr(10).join(f"- {area}" for area in focus_areas)}
"""

    prompt = f"""You are conducting a follow-up code review of a GitLab merge request based on additional context provided by the user.

## Merge Request Information

**Title:** {mr_data.get("title", "Unknown")}
**State:** {mr_data.get("state", "unknown")}
**Labels:** {labels_text}
**Author:** {mr_data.get("author", {}).get("username", "Unknown")}
**Source Branch:** {mr_data.get("source_branch", "unknown")} → **Target Branch:** {mr_data.get("target_branch", "unknown")}
**Created:** {mr_data.get("created_at", "Unknown")}

## Description

{mr_data.get("description", "No description provided.")}
{previous_context}
## User's Additional Context/Questions

{additional_context}
{focus_text}
## Code Changes

```diff
{diff_content}
```

{"**Note:** Diff truncated to first 15000 characters for analysis." if truncated else ""}

## Your Task

Based on the user's additional context and questions above, provide a focused code review response. Address the specific concerns or questions raised while maintaining comprehensive review quality.

Provide your response in the following JSON format:

```json
{{
  "summary": "Summary addressing the user's specific questions/concerns",
  "review_status": "approved|needs_work|blocked",
  "code_quality": "excellent|good|needs_improvement|poor",
  "findings": [
    {{
      "severity": "critical|major|minor|suggestion",
      "category": "bug|security|performance|style|best_practice|documentation|testing|other",
      "file": "path/to/file.py",
      "line": 42,
      "message": "Clear description of the finding",
      "suggestion": "Specific recommendation for improvement"
    }}
  ],
  "security_concerns": [
    "Specific security issue or concern"
  ],
  "performance_notes": [
    "Performance consideration or optimization opportunity"
  ],
  "test_coverage": "Assessment of whether changes are adequately tested",
  "user_questions_addressed": [
    {{
      "question": "The user's question or concern",
      "answer": "Your specific answer addressing this point"
    }}
  ]
}}
```

**Important:**
- Prioritize answering the user's specific questions and concerns
- Reference the previous review context if provided
- Focus on the requested areas if specified
- Maintain objectivity and constructive tone
- Provide actionable, specific recommendations

Respond with ONLY the JSON object, no other text."""

    return prompt


def _parse_mr_review_response(response_content: str) -> dict:
    """Parse the AI's code review response and extract structured data."""

    # Try to extract JSON from the response
    try:
        # Look for JSON code block
        if "```json" in response_content:
            start = response_content.find("```json") + 7
            end = response_content.find("```", start)
            json_text = response_content[start:end].strip()
        elif "```" in response_content:
            start = response_content.find("```") + 3
            end = response_content.find("```", start)
            json_text = response_content[start:end].strip()
        else:
            # Try to parse the whole response as JSON
            json_text = response_content.strip()

        review = json.loads(json_text)

        # Validate required fields
        required_fields = ["summary", "review_status", "code_quality", "findings", "security_concerns", "performance_notes", "test_coverage"]
        for field in required_fields:
            if field not in review:
                if field in ["findings", "security_concerns", "performance_notes"]:
                    review[field] = []
                else:
                    review[field] = None

        return review

    except json.JSONDecodeError:
        # If JSON parsing fails, return a basic structure
        return {
            "summary": "AI code review completed but response format was invalid.",
            "review_status": "needs_work",
            "code_quality": "unknown",
            "findings": [],
            "security_concerns": [],
            "performance_notes": [],
            "test_coverage": "Unable to assess - please review manually",
            "raw_response": response_content[:500]  # Include first 500 chars for debugging
        }


def _format_finding_as_comment(finding: dict, review_data: dict) -> str:
    """
    Format a code review finding as a markdown comment for posting to GitLab MR.

    Args:
        finding: The finding dict with severity, category, description, location, suggestion
        review_data: The full review data for context

    Returns:
        Formatted markdown comment string
    """
    # Extract finding details
    severity = finding.get("severity", "unknown").upper()
    category = finding.get("category", "other").replace("_", " ").title()
    description = finding.get("description", "No description provided")
    location = finding.get("location", "")
    suggestion = finding.get("suggestion", "")

    # Choose emoji based on severity
    severity_emoji_map = {
        "CRITICAL": "🚨",
        "MAJOR": "⚠️",
        "MINOR": "💡",
        "SUGGESTION": "💭"
    }
    emoji = severity_emoji_map.get(severity, "📝")

    # Build markdown comment
    comment_parts = []

    # Header with severity and category
    comment_parts.append(f"## {emoji} **{severity}** - {category}")
    comment_parts.append("")

    # Description
    comment_parts.append(f"**Issue:** {description}")
    comment_parts.append("")

    # Location (if provided)
    if location:
        comment_parts.append(f"**Location:** `{location}`")
        comment_parts.append("")

    # Suggestion (if provided)
    if suggestion:
        comment_parts.append(f"**Suggestion:** {suggestion}")
        comment_parts.append("")

    # Footer with AI attribution
    comment_parts.append("---")
    comment_parts.append("_🤖 Generated by AI Code Review_")

    return "\n".join(comment_parts)


# ============================================
# GitLab CLI Check & Auth
# ============================================

@router.get("/cli/check")
async def check_gitlab_cli():
    """Check if GitLab CLI is installed."""
    result = run_glab_command(["--version"])
    return {"success": True, "data": {"installed": result["success"]}}


@router.post("/cli/install")
async def install_gitlab_cli():
    """Provide instructions to install GitLab CLI."""
    return {
        "success": True,
        "data": {
            "message": "Install glab: https://gitlab.com/gitlab-org/cli#installation"
        }
    }


@router.get("/auth/check")
async def check_gitlab_auth(hostname: str | None = Query(None)):
    """Check if user is authenticated with GitLab CLI."""
    args = ["auth", "status"]
    if hostname:
        args.extend(["--hostname", hostname])
    result = run_glab_command(args)
    authenticated = result["success"] and "Logged in" in result.get("output", "")
    return {"success": True, "data": {"authenticated": authenticated}}


@router.post("/auth/start")
async def start_gitlab_auth(hostname: str | None = None):
    """Start GitLab CLI authentication flow."""
    return {
        "success": True,
        "data": {
            "success": False,
            "message": "Run 'glab auth login' in terminal to authenticate"
        }
    }


@router.get("/token")
async def get_gitlab_token(hostname: str | None = Query(None)):
    """Get GitLab auth token from CLI."""
    # glab stores tokens in config, we can try to get it
    return {"success": True, "data": {"token": ""}}


@router.get("/user")
async def get_gitlab_user(hostname: str | None = Query(None)):
    """Get authenticated GitLab username."""
    result = run_glab_command(["api", "user", "-q", ".username"])
    if result["success"]:
        return {"success": True, "data": {"username": result["output"]}}
    return {"success": True, "data": {"username": ""}}


@router.get("/projects")
async def list_gitlab_user_projects(hostname: str | None = Query(None)):
    """List projects for authenticated user."""
    result = run_glab_command([
        "api", "projects", "--method", "GET",
        "-f", "membership=true", "-f", "per_page=100"
    ])
    if result["success"]:
        try:
            projects = json.loads(result["output"])
            return {"success": True, "data": {"projects": projects}}
        except json.JSONDecodeError:
            return {"success": True, "data": {"projects": []}}
    return {"success": True, "data": {"projects": []}}


@router.get("/groups")
async def list_gitlab_groups(hostname: str | None = Query(None)):
    """List groups for authenticated user."""
    result = run_glab_command(["api", "groups", "-f", "per_page=100"])
    if result["success"]:
        try:
            groups = json.loads(result["output"])
            return {"success": True, "data": {"groups": groups}}
        except json.JSONDecodeError:
            return {"success": True, "data": {"groups": []}}
    return {"success": True, "data": {"groups": []}}


@router.get("/detect-project")
async def detect_gitlab_project(path: str = Query(...)):
    """Detect GitLab remote for a local repository."""
    result = run_glab_command(["repo", "view", "-o", "json"], cwd=path)
    if result["success"]:
        try:
            project = json.loads(result["output"])
            return {"success": True, "data": project.get("path_with_namespace", "")}
        except json.JSONDecodeError:
            pass
    return {"success": True, "data": ""}


@router.get("/branches")
async def get_gitlab_branches(
    path: str = Query(...),
    token: str = Query(...),
    instanceUrl: str | None = Query(None)
):
    """Get branches for a GitLab project."""
    result = run_glab_command(["api", "projects/:id/repository/branches", "-f", "per_page=100"], cwd=path)
    if result["success"]:
        try:
            branches = json.loads(result["output"])
            return {"success": True, "data": [b["name"] for b in branches]}
        except json.JSONDecodeError:
            pass
    return {"success": True, "data": []}


@router.post("/projects")
async def create_gitlab_project(request: CreateProjectRequest):
    """Create a new GitLab project."""
    args = ["repo", "create", request.projectName]
    if request.description:
        args.extend(["--description", request.description])
    args.extend(["--visibility", request.visibility])

    result = run_glab_command(args)
    if result["success"]:
        return {
            "success": True,
            "data": {
                "pathWithNamespace": request.projectName,
                "webUrl": ""
            }
        }
    return {"success": False, "error": result.get("error", "Failed to create project")}


@router.post("/remote")
async def add_gitlab_remote(request: AddRemoteRequest):
    """Add GitLab remote to local repository."""
    instance = request.instanceUrl or "https://gitlab.com"
    remote_url = f"{instance}/{request.projectPathWithNamespace}.git"
    try:
        subprocess.run(
            ["git", "remote", "add", "origin", remote_url],
            cwd=request.projectPath,
            check=True,
            capture_output=True
        )
        return {"success": True, "data": {"remoteUrl": remote_url}}
    except subprocess.CalledProcessError as e:
        return {"success": False, "error": e.stderr.decode() if e.stderr else "Failed to add remote"}


# ============================================
# Project-specific GitLab Routes
# These are mounted under /api/projects/{projectId}/gitlab
# ============================================

project_router = APIRouter()


@project_router.get("/projects")
async def get_project_gitlab_projects(projectId: str):
    """Get GitLab projects for a project."""
    return {"success": True, "data": []}


@project_router.get("/status")
async def check_project_gitlab_connection(projectId: str):
    """Check GitLab connection status for a project."""
    return {
        "success": True,
        "data": {
            "connected": False,
            "projectPath": None,
            "error": None
        }
    }


@project_router.get("/issues")
async def get_project_gitlab_issues(
    projectId: str,
    state: str | None = Query(None)
):
    """Get GitLab issues for a project."""
    return {"success": True, "data": []}


@project_router.get("/issues/{issueIid}")
async def get_project_gitlab_issue(projectId: str, issueIid: int):
    """Get a specific GitLab issue."""
    return {"success": True, "data": None}


@project_router.get("/issues/{issueIid}/notes")
async def get_project_gitlab_issue_notes(projectId: str, issueIid: int):
    """Get notes for a GitLab issue."""
    return {"success": True, "data": []}


@project_router.post("/issues/{issueIid}/investigate")
async def investigate_gitlab_issue(
    projectId: str,
    issueIid: int,
    request: InvestigateRequest
):
    """Investigate a GitLab issue using AI."""
    try:
        # Load projects and validate project exists
        from .projects import load_projects

        projects = load_projects()
        if projectId not in projects:
            return {"success": False, "error": f"Project {projectId} not found"}

        project_path = FilePath(projects[projectId]["path"])

        # Fetch issue details using glab CLI
        issue_result = run_glab_command(
            ["api", f"projects/:id/issues/{issueIid}"],
            cwd=str(project_path)
        )

        if not issue_result["success"]:
            return {
                "success": False,
                "error": f"Failed to fetch issue: {issue_result.get('error', 'Unknown error')}"
            }

        try:
            issue_data = json.loads(issue_result["output"])
        except json.JSONDecodeError:
            return {"success": False, "error": "Failed to parse issue data"}

        # Fetch all notes for the issue
        notes_result = run_glab_command(
            ["api", f"projects/:id/issues/{issueIid}/notes", "-f", "per_page=100"],
            cwd=str(project_path)
        )

        all_notes = []
        if notes_result["success"]:
            try:
                all_notes = json.loads(notes_result["output"])
            except json.JSONDecodeError:
                pass

        # Filter notes if specific IDs were selected
        selected_notes = []
        if request.selectedNoteIds:
            selected_notes = [
                note for note in all_notes
                if note.get("id") in request.selectedNoteIds
            ]
        else:
            # If no specific notes selected, include all notes
            selected_notes = all_notes

        # Prepare issue data for analysis
        issue_info = {
            "iid": issue_data.get("iid"),
            "title": issue_data.get("title"),
            "description": issue_data.get("description"),
            "state": issue_data.get("state"),
            "labels": issue_data.get("labels", []),
            "author": issue_data.get("author", {}),
            "created_at": issue_data.get("created_at"),
            "updated_at": issue_data.get("updated_at"),
            "web_url": issue_data.get("web_url"),
        }

        # Perform AI analysis
        try:
            analysis_result = await analyze_issue_with_ai(
                issue_info,
                selected_notes,
                str(project_path)
            )
            analysis_status = "completed"
            analysis_data = analysis_result
        except Exception as ai_error:
            # If AI analysis fails, still return the issue data
            analysis_status = "failed"
            analysis_data = {
                "error": f"AI analysis failed: {str(ai_error)}",
                "summary": None,
                "issue_type": None,
                "complexity": None,
                "suggestions": [],
                "affected_areas": [],
                "risks": []
            }

        # Prepare investigation data
        investigation_data = {
            "issue": issue_info,
            "notes": selected_notes,
            "analysis": {
                "status": analysis_status,
                **analysis_data
            }
        }

        return {
            "success": True,
            "data": investigation_data
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to investigate issue: {str(e)}"
        }


@project_router.post("/import")
async def import_gitlab_issues(projectId: str, request: ImportIssuesRequest):
    """Import GitLab issues as tasks."""
    return {
        "success": True,
        "data": {
            "success": True,
            "imported": 0,
            "failed": 0,
            "issues": []
        }
    }


# ============================================
# Merge Request Routes
# ============================================

@project_router.get("/merge-requests")
async def get_project_merge_requests(
    projectId: str,
    state: str | None = Query(None)
):
    """Get merge requests for a project."""
    return {"success": True, "data": []}


@project_router.get("/merge-requests/{mrIid}")
async def get_project_merge_request(projectId: str, mrIid: int):
    """Get a specific merge request."""
    return {"success": True, "data": None}


@project_router.post("/merge-requests")
async def create_merge_request(projectId: str, request: CreateMRRequest):
    """Create a new merge request."""
    return {"success": True, "data": None}


@project_router.patch("/merge-requests/{mrIid}")
async def update_merge_request(projectId: str, mrIid: int, request: UpdateMRRequest):
    """
    Update a merge request title, description, and/or labels using glab CLI.

    Uses partial updates - only updates fields that are provided in the request.
    Executes: glab mr update <mrIid> --title <title> --description <description> --label <labels>

    Args:
        projectId: The project ID from the database
        mrIid: The merge request IID (internal ID)
        request: UpdateMRRequest with optional title, description, and labels

    Returns:
        Success response or error with details
    """
    try:
        # Import here to avoid circular dependency
        from .projects import load_projects

        # Validate project exists and get project path
        projects = load_projects()
        if projectId not in projects:
            raise HTTPException(
                status_code=404,
                detail=f"Project {projectId} not found"
            )

        project_path = projects[projectId]["path"]

        # Validate at least one field is provided for update
        if not request.title and not request.description and not request.labels:
            return {
                "success": False,
                "error": "At least one field (title, description, or labels) must be provided for update"
            }

        # Build glab command with only provided fields
        args = ["mr", "update", str(mrIid)]

        if request.title is not None:
            # Strip whitespace and validate title is not empty
            title = request.title.strip()
            if not title:
                return {"success": False, "error": "Title cannot be empty"}
            args.extend(["--title", title])

        if request.description is not None:
            # Description can be empty (to clear it), so just use the value as-is
            args.extend(["--description", request.description])

        if request.labels is not None:
            # Labels should be a comma-separated string for glab
            if len(request.labels) > 0:
                labels_str = ",".join(request.labels)
                args.extend(["--label", labels_str])

        # Run glab command in the project directory
        result = run_glab_command(args, cwd=project_path)

        if not result["success"]:
            return {
                "success": False,
                "error": f"Failed to update merge request: {result['error']}"
            }

        # Success - return the result
        return {
            "success": True,
            "message": f"Merge request !{mrIid} updated successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to update merge request: {str(e)}"
        }


@project_router.patch("/merge-requests/{mrIid}/assign")
async def assign_merge_request(projectId: str, mrIid: int, request: AssignMRRequest):
    """
    Assign users to a merge request using glab CLI.

    Executes: glab mr update <mrIid> --assignee <userId1> --assignee <userId2> ...

    Args:
        projectId: The project ID from the database
        mrIid: The merge request IID (internal ID)
        request: AssignMRRequest with list of user IDs to assign

    Returns:
        Success response or error with details
    """
    try:
        # Import here to avoid circular dependency
        from .projects import load_projects

        # Validate project exists and get project path
        projects = load_projects()
        if projectId not in projects:
            raise HTTPException(
                status_code=404,
                detail=f"Project {projectId} not found"
            )

        project_path = projects[projectId]["path"]

        # Validate userIds are provided
        if not request.userIds or len(request.userIds) == 0:
            return {
                "success": False,
                "error": "At least one user ID must be provided for assignment"
            }

        # Build glab command with assignee flags
        # glab uses --assignee flag (can be repeated for multiple assignees)
        args = ["mr", "update", str(mrIid)]

        # Add each user ID as an assignee
        # GitLab accepts user IDs as assignees
        for userId in request.userIds:
            args.extend(["--assignee", str(userId)])

        # Run glab command in the project directory
        result = run_glab_command(args, cwd=project_path)

        if not result["success"]:
            return {
                "success": False,
                "error": f"Failed to assign users to merge request: {result['error']}"
            }

        # Success - return the result
        user_count = len(request.userIds)
        user_text = "user" if user_count == 1 else "users"
        return {
            "success": True,
            "message": f"Successfully assigned {user_count} {user_text} to merge request !{mrIid}"
        }

    except HTTPException:
        raise
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to assign users to merge request: {str(e)}"
        }


@project_router.post("/merge-requests/{mrIid}/approve")
async def approve_merge_request(projectId: str, mrIid: int):
    """
    Approve a merge request using glab CLI.

    Executes: glab mr approve <mrIid>

    Args:
        projectId: The project ID from the database
        mrIid: The merge request IID (internal ID) to approve

    Returns:
        Success response or error with details
    """
    try:
        # Import here to avoid circular dependency
        from .projects import load_projects

        # Validate project exists and get project path
        projects = load_projects()
        if projectId not in projects:
            raise HTTPException(
                status_code=404,
                detail=f"Project {projectId} not found"
            )

        project_path = projects[projectId]["path"]

        # Build glab command to approve the merge request
        args = ["mr", "approve", str(mrIid)]

        # Run glab command in the project directory
        result = run_glab_command(args, cwd=project_path)

        if not result["success"]:
            return {
                "success": False,
                "error": f"Failed to approve merge request: {result['error']}"
            }

        # Success - return the result
        return {
            "success": True,
            "message": f"Merge request !{mrIid} approved successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to approve merge request: {str(e)}"
        }


@project_router.post("/merge-requests/{mrIid}/merge")
async def merge_merge_request(projectId: str, mrIid: int, request: MergeRequest):
    """
    Merge a merge request using glab CLI with safety checks.

    CRITICAL: This is an irreversible operation. The glab CLI will prompt for
    confirmation before merging. Do not use --yes flag to skip confirmation.

    Supports different merge methods:
    - "merge": Standard merge (default)
    - "squash": Squash all commits into a single commit
    - "rebase": Rebase source branch before merging

    Executes: glab mr merge <mrIid> [--squash | --rebase]

    Args:
        projectId: The project ID from the database
        mrIid: The merge request IID (internal ID)
        request: MergeRequest with optional mergeMethod

    Returns:
        Success response or error with details

    Safety Features:
        - Validates project exists
        - Validates merge method if provided
        - Does NOT skip glab confirmation prompts
        - glab CLI will check MR status before merging
    """
    try:
        # Import here to avoid circular dependency
        from .projects import load_projects

        # Validate project exists and get project path
        projects = load_projects()
        if projectId not in projects:
            raise HTTPException(
                status_code=404,
                detail=f"Project {projectId} not found"
            )

        project_path = projects[projectId]["path"]

        # Build glab merge command
        args = ["mr", "merge", str(mrIid)]

        # Add merge method if provided
        if request.mergeMethod:
            method = request.mergeMethod.strip().lower()

            # Validate merge method
            valid_methods = ["merge", "squash", "rebase"]
            if method not in valid_methods:
                return {
                    "success": False,
                    "error": f"Invalid merge method '{request.mergeMethod}'. Must be one of: {', '.join(valid_methods)}"
                }

            # Add corresponding flag (only for squash and rebase, merge is default)
            if method == "squash":
                args.append("--squash")
            elif method == "rebase":
                args.append("--rebase")
            # method == "merge" is the default, no flag needed

        # SAFETY: Do NOT add --yes flag to skip confirmation prompts
        # Let glab CLI prompt the user for confirmation before merging

        # Run glab command in the project directory
        result = run_glab_command(args, cwd=project_path)

        if not result["success"]:
            return {
                "success": False,
                "error": f"Failed to merge merge request: {result['error']}"
            }

        # Success - return the result
        return {
            "success": True,
            "message": f"Merge request !{mrIid} merged successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to merge merge request: {str(e)}"
        }


@project_router.post("/merge-requests/{mrIid}/notes")
async def post_mr_note(projectId: str, mrIid: int, request: PostNoteRequest):
    """
    Post a note (comment) on a merge request using glab CLI.

    Posts a comment/note to a GitLab merge request. The note is visible to all
    users with access to the merge request and can include markdown formatting.

    Executes: glab mr note <mrIid> --message <body>

    Args:
        projectId: The project ID from the database
        mrIid: The merge request IID (internal ID)
        request: PostNoteRequest with the note body (message text)

    Returns:
        Success response or error with details

    Validation:
        - Validates project exists
        - Validates note body is not empty
        - Strips leading/trailing whitespace from body
    """
    try:
        # Import here to avoid circular dependency
        from .projects import load_projects

        # Validate project exists and get project path
        projects = load_projects()
        if projectId not in projects:
            raise HTTPException(
                status_code=404,
                detail=f"Project {projectId} not found"
            )

        project_path = projects[projectId]["path"]

        # Validate note body is not empty
        if not request.body or not request.body.strip():
            return {"success": False, "error": "Note body cannot be empty"}

        # Strip whitespace from body
        body = request.body.strip()

        # Build glab note command
        # glab mr note <mrIid> --message <body>
        args = ["mr", "note", str(mrIid), "--message", body]

        # Execute glab command in project directory
        result = run_glab_command(args, cwd=project_path)

        if not result["success"]:
            return {
                "success": False,
                "error": f"Failed to post note on merge request: {result['error']}"
            }

        return {
            "success": True,
            "message": f"Note posted successfully on merge request !{mrIid}"
        }

    except HTTPException:
        # Re-raise HTTPException for FastAPI to handle
        raise
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to post note on merge request: {str(e)}"
        }


# MR Review routes
@project_router.get("/merge-requests/{mrIid}/review")
async def get_mr_review(projectId: str, mrIid: int):
    """Get review for a merge request."""
    return {"success": True, "data": None}


@project_router.post("/merge-requests/{mrIid}/review/run")
async def run_mr_review(projectId: str, mrIid: int):
    """
    Run AI-powered code review on a merge request.

    This endpoint:
    1. Fetches MR details and metadata from GitLab
    2. Fetches the diff showing all code changes
    3. Analyzes the code with AI for quality, security, and best practices
    4. Returns structured code review findings

    Args:
        projectId: Project identifier
        mrIid: Merge request internal ID (IID)

    Returns:
        success: Whether the operation succeeded
        data: {
            merge_request: MR metadata
            review: AI code review analysis with findings
        }
    """
    try:
        # Load projects and validate project exists
        from .projects import load_projects

        projects = load_projects()
        if projectId not in projects:
            return {"success": False, "error": f"Project {projectId} not found"}

        project_path = FilePath(projects[projectId]["path"])

        # Fetch MR details using glab CLI
        mr_result = run_glab_command(
            ["api", f"projects/:id/merge_requests/{mrIid}"],
            cwd=str(project_path)
        )

        if not mr_result["success"]:
            return {
                "success": False,
                "error": f"Failed to fetch merge request: {mr_result.get('error', 'Unknown error')}"
            }

        try:
            mr_data = json.loads(mr_result["output"])
        except json.JSONDecodeError:
            return {"success": False, "error": "Failed to parse merge request data"}

        # Fetch MR diff (changes) using glab CLI
        # Use the changes API endpoint to get the full diff
        diff_result = run_glab_command(
            ["api", f"projects/:id/merge_requests/{mrIid}/changes"],
            cwd=str(project_path)
        )

        diff_content = ""
        if diff_result["success"]:
            try:
                changes_data = json.loads(diff_result["output"])
                # Extract diffs from all changed files
                changes = changes_data.get("changes", [])

                for change in changes:
                    file_path = change.get("new_path") or change.get("old_path")
                    diff = change.get("diff", "")

                    # Format as unified diff
                    if diff:
                        diff_content += f"\n--- a/{change.get('old_path', file_path)}\n"
                        diff_content += f"+++ b/{change.get('new_path', file_path)}\n"
                        diff_content += diff + "\n"

                if not diff_content:
                    diff_content = "No changes detected in this merge request."

            except json.JSONDecodeError:
                diff_content = "Failed to parse diff data - may be too large or malformed."
        else:
            diff_content = "Failed to fetch diff from GitLab API."

        # Prepare MR data for analysis
        mr_info = {
            "iid": mr_data.get("iid"),
            "title": mr_data.get("title"),
            "description": mr_data.get("description"),
            "state": mr_data.get("state"),
            "labels": mr_data.get("labels", []),
            "author": mr_data.get("author", {}),
            "source_branch": mr_data.get("source_branch"),
            "target_branch": mr_data.get("target_branch"),
            "created_at": mr_data.get("created_at"),
            "updated_at": mr_data.get("updated_at"),
            "web_url": mr_data.get("web_url"),
        }

        # Perform AI code review
        try:
            review_result = await analyze_mr_with_ai(
                mr_info,
                diff_content,
                str(project_path)
            )
            review_status = "completed"
            review_data = review_result
        except Exception as ai_error:
            # If AI analysis fails, still return the MR data
            review_status = "failed"
            review_data = {
                "error": f"AI code review failed: {str(ai_error)}",
                "summary": None,
                "review_status": None,
                "code_quality": None,
                "findings": [],
                "security_concerns": [],
                "performance_notes": [],
                "test_coverage": None
            }

        # Prepare review response data
        review_response = {
            "merge_request": mr_info,
            "review": {
                "status": review_status,
                **review_data
            }
        }

        return {
            "success": True,
            "data": review_response
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to run MR review: {str(e)}"
        }


@project_router.post("/merge-requests/{mrIid}/review/followup")
async def run_mr_followup_review(projectId: str, mrIid: int, request: FollowupReviewRequest):
    """
    Run a follow-up AI code review on a merge request with additional user context.

    This endpoint allows users to ask specific questions or provide additional context
    about a merge request, building on previous review findings. Perfect for:
    - Asking specific questions about the code changes
    - Getting clarification on previous review findings
    - Focusing on specific aspects of the code
    - Re-reviewing after code updates

    Args:
        projectId: Project identifier
        mrIid: Merge request internal ID (IID)
        request: FollowupReviewRequest with:
            - additionalContext: User's questions or additional context (required)
            - previousReview: Optional previous review findings for context
            - focusAreas: Optional list of specific areas to focus on

    Returns:
        success: Whether the operation succeeded
        data: {
            merge_request: MR metadata
            review: AI code review analysis addressing user's questions
        }

    Example use cases:
        - "Can you explain the security implications of the changes in auth.py?"
        - "Are there any performance concerns with the database queries?"
        - "How does this change affect backwards compatibility?"
    """
    try:
        # Import here to avoid circular dependency
        from .projects import load_projects

        # Validate project exists and get project path
        projects = load_projects()
        if projectId not in projects:
            raise HTTPException(
                status_code=404,
                detail=f"Project {projectId} not found"
            )

        project_path = projects[projectId]["path"]

        # Validate additionalContext is not empty
        if not request.additionalContext or not request.additionalContext.strip():
            return {
                "success": False,
                "error": "Additional context or questions must be provided for follow-up review"
            }

        # Fetch MR details using glab CLI
        args = ["mr", "view", str(mrIid), "--json"]
        result = run_glab_command(args, cwd=project_path)

        if not result["success"]:
            return {
                "success": False,
                "error": f"Failed to fetch merge request: {result['error']}"
            }

        try:
            mr_data = json.loads(result["output"])
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"Failed to parse merge request data: {str(e)}"
            }

        # Fetch MR diff for code analysis
        diff_args = ["mr", "diff", str(mrIid)]
        diff_result = run_glab_command(diff_args, cwd=project_path)

        if not diff_result["success"]:
            return {
                "success": False,
                "error": f"Failed to fetch merge request diff: {diff_result['error']}"
            }

        diff_content = diff_result["output"]

        # Add backend to Python path for AI client
        backend_path = FilePath(__file__).parent.parent.parent.parent / "backend"
        if str(backend_path) not in sys.path:
            sys.path.insert(0, str(backend_path))

        try:
            from core.simple_client import create_simple_client
        except ImportError as e:
            return {
                "success": False,
                "error": f"Failed to import AI client: {str(e)}"
            }

        # Build followup review prompt with user's context
        prompt = _build_followup_review_prompt(
            mr_data=mr_data,
            diff_content=diff_content,
            additional_context=request.additionalContext,
            previous_review=request.previousReview,
            focus_areas=request.focusAreas
        )

        # Create AI client for follow-up review
        try:
            client = create_simple_client(
                agent_type="batch_analysis",  # Read-only analysis agent
                model="claude-sonnet-4-20250514",  # Use Sonnet for better code review
                cwd=FilePath(project_path),
                max_turns=1  # Single-turn analysis
            )
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to create AI client: {str(e)}"
            }

        # Run AI follow-up review
        try:
            response = await client.send_message(prompt)

            # Extract review from response
            review = _parse_mr_review_response(response.content)

            # Enhance review with user_questions_addressed if not present
            if "user_questions_addressed" not in review:
                review["user_questions_addressed"] = []

            review_response = {
                "merge_request": {
                    "iid": mr_data.get("iid"),
                    "title": mr_data.get("title"),
                    "state": mr_data.get("state"),
                    "author": mr_data.get("author", {}).get("username"),
                    "source_branch": mr_data.get("source_branch"),
                    "target_branch": mr_data.get("target_branch"),
                    "web_url": mr_data.get("web_url")
                },
                "review": review,
                "context": {
                    "additional_context": request.additionalContext,
                    "focus_areas": request.focusAreas,
                    "had_previous_review": request.previousReview is not None
                }
            }

            return {
                "success": True,
                "data": review_response
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"AI review analysis failed: {str(e)}"
            }

    except HTTPException:
        raise
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to run follow-up MR review: {str(e)}"
        }


@project_router.post("/merge-requests/{mrIid}/review/post")
async def post_mr_review(projectId: str, mrIid: int, request: PostReviewRequest):
    """
    Post AI code review findings as comments to a GitLab merge request.

    This endpoint takes review findings from run_mr_review and posts them as
    individual comments on the merge request. Each finding is formatted as a
    markdown comment with severity, category, description, location, and
    suggestions.

    Args:
        projectId: The project ID from the database
        mrIid: The merge request IID (internal ID)
        request: PostReviewRequest with optional reviewFindings and selectedFindingIds

    Returns:
        Success response with count of posted comments, or error with details

    Workflow:
        1. Validate project exists
        2. Get review findings (from request or re-run review)
        3. Filter findings by selectedFindingIds if provided
        4. Format each finding as a markdown comment
        5. Post each finding as a separate comment using glab CLI
    """
    try:
        # Import here to avoid circular dependency
        from .projects import load_projects

        # Validate project exists and get project path
        projects = load_projects()
        if projectId not in projects:
            raise HTTPException(
                status_code=404,
                detail=f"Project {projectId} not found"
            )

        project_path = projects[projectId]["path"]

        # Get review findings - either from request or re-run the review
        review_data = None
        if request.reviewFindings:
            # Use the provided review findings
            review_data = request.reviewFindings
        else:
            # Re-run the review to get latest findings
            # This is less efficient but ensures we have fresh data
            review_result = await run_mr_review(projectId, mrIid)

            if not review_result.get("success"):
                return {
                    "success": False,
                    "error": f"Failed to get review findings: {review_result.get('error', 'Unknown error')}"
                }

            review_data = review_result.get("data", {}).get("review", {})

        # Validate we have review data
        if not review_data:
            return {
                "success": False,
                "error": "No review findings available. Please run the review first."
            }

        # Extract findings from review data
        findings = review_data.get("findings", [])

        if not findings or len(findings) == 0:
            return {
                "success": True,
                "message": "No findings to post",
                "posted_count": 0
            }

        # Filter findings by selectedFindingIds if provided
        findings_to_post = findings
        if request.selectedFindingIds and len(request.selectedFindingIds) > 0:
            # Create a set for faster lookup
            selected_ids = set(request.selectedFindingIds)
            findings_to_post = [
                finding for finding in findings
                if finding.get("id") in selected_ids
            ]

            if not findings_to_post:
                return {
                    "success": False,
                    "error": "None of the selected findings were found in the review data"
                }

        # Post each finding as a separate comment
        posted_count = 0
        failed_count = 0
        errors = []

        for finding in findings_to_post:
            # Format finding as markdown comment
            comment = _format_finding_as_comment(finding, review_data)

            # Post comment using glab CLI
            args = ["mr", "note", str(mrIid), "--message", comment]
            result = run_glab_command(args, cwd=project_path)

            if result["success"]:
                posted_count += 1
            else:
                failed_count += 1
                error_msg = result.get("error", "Unknown error")
                errors.append(f"Failed to post finding: {error_msg}")

        # Prepare response
        if failed_count == 0:
            return {
                "success": True,
                "message": f"Successfully posted {posted_count} review findings to merge request !{mrIid}",
                "posted_count": posted_count
            }
        elif posted_count > 0:
            # Partial success
            return {
                "success": True,
                "message": f"Posted {posted_count} findings, but {failed_count} failed",
                "posted_count": posted_count,
                "failed_count": failed_count,
                "errors": errors
            }
        else:
            # All failed
            return {
                "success": False,
                "error": f"Failed to post any findings ({failed_count} failures)",
                "errors": errors
            }

    except HTTPException:
        # Re-raise HTTPException for FastAPI to handle
        raise
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to post review findings: {str(e)}"
        }


@project_router.post("/merge-requests/{mrIid}/review/cancel")
async def cancel_mr_review(projectId: str, mrIid: int):
    """
    Cancel ongoing MR review process.

    Note: In the current architecture, MR reviews run synchronously within
    the HTTP request and complete before returning a response. There are no
    background review processes to cancel.

    To stop a review that's currently running:
    - Close or cancel the HTTP request in your client
    - Refresh the page to abort the pending request

    This endpoint is provided for API compatibility and future extensibility
    if background review processing is implemented.

    Args:
        projectId: Project identifier
        mrIid: Merge request internal ID (IID)

    Returns:
        success: Always True (no background process to cancel)
        message: Explanation of the current architecture
        note: Guidance on how to stop a review
    """
    try:
        # Import here to avoid circular dependency
        from .projects import load_projects

        # Validate project exists (for consistency with other endpoints)
        projects = load_projects()
        if projectId not in projects:
            return {
                "success": False,
                "error": f"Project {projectId} not found"
            }

        # Return informative message about current architecture
        return {
            "success": True,
            "message": "MR reviews currently run synchronously within HTTP requests",
            "note": "To stop a review, cancel the HTTP request in your client or refresh the page. No server-side background process exists to cancel.",
            "mrIid": mrIid,
            "architecture": "synchronous"
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to process cancel request: {str(e)}"
        }


@project_router.get("/merge-requests/{mrIid}/new-commits")
async def check_mr_new_commits(projectId: str, mrIid: int):
    """Check for new commits on a merge request."""
    return {
        "success": True,
        "data": {
            "hasNewCommits": False,
            "newCommitCount": 0,
            "latestSha": ""
        }
    }


@project_router.post("/releases")
async def create_gitlab_release(projectId: str, request: CreateReleaseRequest):
    """Create a GitLab release."""
    return {"success": True, "data": {"url": ""}}
