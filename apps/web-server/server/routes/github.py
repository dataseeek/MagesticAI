"""
GitHub integration routes.

Handles GitHub OAuth, repository management, issues, PRs, and releases.
"""

import json
import subprocess
import sys
from pathlib import Path as FilePath

from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter()


# ============================================
# Request/Response Models
# ============================================

class CreateRepoRequest(BaseModel):
    repoName: str
    description: str | None = None
    private: bool = False
    orgName: str | None = None


class AddRemoteRequest(BaseModel):
    projectPath: str
    repoFullName: str


class InvestigateRequest(BaseModel):
    selectedCommentIds: list[int] | None = None


class ImportIssuesRequest(BaseModel):
    issueNumbers: list[int]


class CreateReleaseRequest(BaseModel):
    version: str
    releaseNotes: str
    draft: bool = False
    prerelease: bool = False


# ============================================
# GitHub CLI Helpers
# ============================================

def run_gh_command(args: list[str], cwd: str | None = None) -> dict:
    """Run a gh CLI command and return the result."""
    try:
        result = subprocess.run(
            ["gh"] + args,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=30
        )
        if result.returncode != 0:
            return {"success": False, "error": result.stderr.strip()}
        return {"success": True, "output": result.stdout.strip()}
    except FileNotFoundError:
        return {"success": False, "error": "GitHub CLI (gh) not installed"}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Command timed out"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================
# AI Analysis Helper
# ============================================

async def analyze_issue_with_ai(issue_data: dict, comments: list, project_path: str) -> dict:
    """
    Analyze a GitHub issue using AI.

    Args:
        issue_data: Issue data from GitHub API
        comments: List of comments on the issue
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
    prompt = _build_issue_analysis_prompt(issue_data, comments)

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


def _build_issue_analysis_prompt(issue_data: dict, comments: list) -> str:
    """Build the analysis prompt for the AI."""

    # Format comments for inclusion in prompt
    comments_text = ""
    if comments:
        comments_text = "\n\n## Comments\n\n"
        for comment in comments[:10]:  # Limit to first 10 comments
            author = comment.get("user", {}).get("login", "Unknown")
            body = comment.get("body", "")
            created_at = comment.get("created_at", "")
            comments_text += f"**{author}** ({created_at}):\n{body}\n\n"

    labels_text = ", ".join([label.get("name", "") for label in issue_data.get("labels", [])]) if issue_data.get("labels") else "None"

    prompt = f"""You are analyzing a GitHub issue to help understand what needs to be done and provide actionable insights.

## Issue Information

**Title:** {issue_data.get("title", "Unknown")}
**State:** {issue_data.get("state", "unknown")}
**Labels:** {labels_text}
**Author:** {issue_data.get("user", {}).get("login", "Unknown")}
**Created:** {issue_data.get("created_at", "Unknown")}
**Updated:** {issue_data.get("updated_at", "Unknown")}

## Description

{issue_data.get("body", "No description provided.")}
{comments_text}

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
            "suggestions": [],
            "affected_areas": [],
            "risks": []
        }


# ============================================
# GitHub CLI Check & Auth
# ============================================

@router.get("/cli/check")
async def check_github_cli():
    """Check if GitHub CLI is installed."""
    result = run_gh_command(["--version"])
    return {"success": True, "data": {"installed": result["success"]}}


@router.get("/auth/check")
async def check_github_auth():
    """Check if user is authenticated with GitHub CLI."""
    result = run_gh_command(["auth", "status"])
    authenticated = result["success"] and "Logged in" in result.get("output", "")
    return {"success": True, "data": {"authenticated": authenticated}}


@router.post("/auth/start")
async def start_github_auth():
    """Start GitHub CLI authentication flow."""
    # Note: In web mode, we can't do interactive auth
    # Return instructions for manual auth
    return {
        "success": True,
        "data": {
            "success": False,
            "message": "Run 'gh auth login' in terminal to authenticate"
        }
    }


@router.get("/token")
async def get_github_token():
    """Get GitHub auth token from CLI."""
    result = run_gh_command(["auth", "token"])
    if result["success"]:
        return {"success": True, "data": {"token": result["output"]}}
    return {"success": True, "data": {"token": ""}}


@router.get("/user")
async def get_github_user():
    """Get authenticated GitHub username."""
    result = run_gh_command(["api", "user", "-q", ".login"])
    if result["success"]:
        return {"success": True, "data": {"username": result["output"]}}
    return {"success": True, "data": {"username": ""}}


@router.get("/repos")
async def list_github_user_repos():
    """List repositories for authenticated user."""
    result = run_gh_command([
        "repo", "list", "--json", "name,nameWithOwner,description,isPrivate,url",
        "--limit", "100"
    ])
    if result["success"]:
        try:
            repos = json.loads(result["output"])
            return {"success": True, "data": {"repos": repos}}
        except json.JSONDecodeError:
            return {"success": True, "data": {"repos": []}}
    return {"success": True, "data": {"repos": []}}


@router.get("/orgs")
async def list_github_orgs():
    """List organizations for authenticated user."""
    result = run_gh_command(["api", "user/orgs", "-q", ".[].login"])
    if result["success"]:
        orgs = [{"login": org} for org in result["output"].split("\n") if org]
        return {"success": True, "data": {"orgs": orgs}}
    return {"success": True, "data": {"orgs": []}}


@router.get("/detect-repo")
async def detect_github_repo(path: str = Query(...)):
    """Detect GitHub remote for a local repository."""
    result = run_gh_command(["repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"], cwd=path)
    if result["success"]:
        return {"success": True, "data": result["output"]}
    return {"success": True, "data": ""}


@router.get("/branches")
async def get_github_branches(
    repo: str = Query(...),
    token: str = Query(...)
):
    """Get branches for a GitHub repository."""
    result = run_gh_command([
        "api", f"repos/{repo}/branches", "--jq", ".[].name"
    ])
    if result["success"]:
        branches = result["output"].split("\n") if result["output"] else []
        return {"success": True, "data": branches}
    return {"success": True, "data": []}


@router.post("/repos")
async def create_github_repo(request: CreateRepoRequest):
    """Create a new GitHub repository."""
    args = ["repo", "create", request.repoName, "--confirm"]
    if request.description:
        args.extend(["--description", request.description])
    if request.private:
        args.append("--private")
    else:
        args.append("--public")
    if request.orgName:
        args[2] = f"{request.orgName}/{request.repoName}"

    result = run_gh_command(args)
    if result["success"]:
        return {
            "success": True,
            "data": {
                "fullName": request.repoName,
                "url": f"https://github.com/{request.repoName}"
            }
        }
    return {"success": False, "error": result.get("error", "Failed to create repo")}


@router.post("/remote")
async def add_git_remote(request: AddRemoteRequest):
    """Add GitHub remote to local repository."""
    remote_url = f"https://github.com/{request.repoFullName}.git"
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
# Project-specific GitHub Routes
# These are mounted under /api/projects/{projectId}/github
# ============================================

project_router = APIRouter()


@project_router.get("/repositories")
async def get_project_github_repositories(projectId: str):
    """Get GitHub repositories for a project."""
    # TODO: Implement based on project's GitHub config
    return {"success": True, "data": []}


@project_router.get("/status")
async def check_project_github_connection(projectId: str):
    """Check GitHub connection status for a project."""
    # TODO: Check project's .env for GitHub config
    return {
        "success": True,
        "data": {
            "connected": False,
            "repoFullName": None,
            "error": None
        }
    }


@project_router.get("/issues")
async def get_project_github_issues(
    projectId: str,
    state: str | None = Query(None)
):
    """Get GitHub issues for a project."""
    # TODO: Implement using project's GitHub config
    return {"success": True, "data": []}


@project_router.get("/issues/{issueNumber}")
async def get_project_github_issue(projectId: str, issueNumber: int):
    """Get a specific GitHub issue."""
    return {"success": True, "data": None}


@project_router.get("/issues/{issueNumber}/comments")
async def get_project_github_issue_comments(projectId: str, issueNumber: int):
    """Get comments for a GitHub issue."""
    return {"success": True, "data": []}


@project_router.post("/issues/{issueNumber}/investigate")
async def investigate_github_issue(
    projectId: str,
    issueNumber: int,
    request: InvestigateRequest
):
    """Investigate a GitHub issue using AI."""
    try:
        # Load projects and validate project exists
        from .projects import load_projects

        projects = load_projects()
        if projectId not in projects:
            return {"success": False, "error": f"Project {projectId} not found"}

        project_path = FilePath(projects[projectId]["path"])

        # Fetch issue details using gh CLI
        # Use 'gh issue view' with JSON output
        issue_result = run_gh_command(
            ["issue", "view", str(issueNumber), "--json", "number,title,body,state,labels,user,createdAt,updatedAt,url"],
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

        # Fetch all comments for the issue
        comments_result = run_gh_command(
            ["issue", "view", str(issueNumber), "--json", "comments"],
            cwd=str(project_path)
        )

        all_comments = []
        if comments_result["success"]:
            try:
                comments_data = json.loads(comments_result["output"])
                all_comments = comments_data.get("comments", [])
            except json.JSONDecodeError:
                pass

        # Filter comments if specific IDs were selected
        selected_comments = []
        if request.selectedCommentIds:
            selected_comments = [
                comment for comment in all_comments
                if comment.get("id") in request.selectedCommentIds
            ]
        else:
            # If no specific comments selected, include all comments
            selected_comments = all_comments

        # Prepare issue data for analysis
        issue_info = {
            "number": issue_data.get("number"),
            "title": issue_data.get("title"),
            "body": issue_data.get("body"),
            "state": issue_data.get("state"),
            "labels": issue_data.get("labels", []),
            "user": issue_data.get("user", {}),
            "created_at": issue_data.get("createdAt"),
            "updated_at": issue_data.get("updatedAt"),
            "url": issue_data.get("url"),
        }

        # Perform AI analysis
        try:
            analysis_result = await analyze_issue_with_ai(
                issue_info,
                selected_comments,
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
            "comments": selected_comments,
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
async def import_github_issues(projectId: str, request: ImportIssuesRequest):
    """Import GitHub issues as tasks."""
    return {
        "success": True,
        "data": {
            "success": True,
            "imported": 0,
            "failed": 0,
            "issues": []
        }
    }


@project_router.post("/releases")
async def create_github_release(projectId: str, request: CreateReleaseRequest):
    """Create a GitHub release."""
    # TODO: Implement release creation
    return {"success": True, "data": {"url": ""}}
