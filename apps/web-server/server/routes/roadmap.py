"""
Roadmap and Ideation routes.

Handles AI-powered roadmap generation and idea management.
"""

import json
from pathlib import Path as FilePath

from fastapi import APIRouter, Path
from pydantic import BaseModel

router = APIRouter()


# ============================================
# Request/Response Models
# ============================================

class RoadmapGenerateRequest(BaseModel):
    enableCompetitorAnalysis: bool | None = False
    refreshCompetitorAnalysis: bool | None = False


class FeatureStatusUpdate(BaseModel):
    status: str  # 'planned', 'in_progress', 'completed', 'cancelled'


class IdeationConfig(BaseModel):
    types: list[str] = ["features", "improvements", "bugfixes"]
    context: str | None = None
    maxIdeas: int = 10


class IdeaStatusUpdate(BaseModel):
    status: str  # 'new', 'accepted', 'rejected', 'archived'


class DeleteIdeasRequest(BaseModel):
    ideaIds: list[str]


# ============================================
# Roadmap Routes
# ============================================

@router.get("")
async def get_roadmap(projectId: str = Path(...)):
    """Get the roadmap for a project."""
    from .projects import load_projects

    projects = load_projects()
    if projectId not in projects:
        return {"success": False, "error": f"Project {projectId} not found"}

    project_path = FilePath(projects[projectId]["path"])
    roadmap_path = project_path / ".auto-claude" / "roadmap.json"

    if not roadmap_path.exists():
        return {"success": True, "data": None}

    try:
        roadmap = json.loads(roadmap_path.read_text())
        return {"success": True, "data": roadmap}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/status")
async def get_roadmap_status(projectId: str = Path(...)):
    """Get the current roadmap generation status."""
    from ..services.roadmap_service import get_roadmap_service

    service = get_roadmap_service()
    status = service.get_status(projectId)

    return {
        "success": True,
        "data": status
    }


@router.put("")
async def save_roadmap(projectId: str = Path(...), roadmap: dict = ...):
    """Save/update the roadmap."""
    from .projects import load_projects

    projects = load_projects()
    if projectId not in projects:
        return {"success": False, "error": f"Project {projectId} not found"}

    project_path = FilePath(projects[projectId]["path"])
    roadmap_path = project_path / ".auto-claude" / "roadmap.json"

    try:
        roadmap_path.parent.mkdir(parents=True, exist_ok=True)
        roadmap_path.write_text(json.dumps(roadmap, indent=2))
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/generate")
async def generate_roadmap(projectId: str = Path(...), request: RoadmapGenerateRequest = ...):
    """Generate a new roadmap using AI."""
    from ..services.roadmap_service import get_roadmap_service
    from .projects import load_projects

    projects = load_projects()
    if projectId not in projects:
        return {"success": False, "error": f"Project {projectId} not found"}

    project_path = FilePath(projects[projectId]["path"])
    service = get_roadmap_service()

    # Check if already running
    if service.is_running(projectId):
        return {"success": False, "error": "Roadmap generation already in progress"}

    # Start generation (runs in background)
    success = await service.start_generation(
        project_id=projectId,
        project_path=project_path,
        enable_competitor_analysis=request.enableCompetitorAnalysis or False,
        refresh_competitor_analysis=request.refreshCompetitorAnalysis or False,
        refresh=False,  # New generation
    )

    return {"success": success}


@router.post("/refresh")
async def refresh_roadmap(projectId: str = Path(...), request: RoadmapGenerateRequest = ...):
    """Refresh/update existing roadmap."""
    from ..services.roadmap_service import get_roadmap_service
    from .projects import load_projects

    projects = load_projects()
    if projectId not in projects:
        return {"success": False, "error": f"Project {projectId} not found"}

    project_path = FilePath(projects[projectId]["path"])
    service = get_roadmap_service()

    # Check if already running
    if service.is_running(projectId):
        return {"success": False, "error": "Roadmap generation already in progress"}

    # Start generation with refresh flag
    success = await service.start_generation(
        project_id=projectId,
        project_path=project_path,
        enable_competitor_analysis=request.enableCompetitorAnalysis or False,
        refresh_competitor_analysis=request.refreshCompetitorAnalysis or False,
        refresh=True,  # Refresh existing
    )

    return {"success": success}


@router.post("/stop")
async def stop_roadmap(projectId: str = Path(...)):
    """Stop ongoing roadmap generation."""
    from ..services.roadmap_service import get_roadmap_service

    service = get_roadmap_service()
    success = await service.stop_generation(projectId)

    return {"success": success}


@router.patch("/features/{featureId}")
async def update_feature_status(
    projectId: str = Path(...),
    featureId: str = Path(...),
    request: FeatureStatusUpdate = ...
):
    """Update a feature's status in roadmap.json."""
    from .projects import load_projects

    try:
        # Validate project exists
        projects = load_projects()
        if projectId not in projects:
            return {"success": False, "error": f"Project {projectId} not found"}

        # Get project path and roadmap file
        project_path = FilePath(projects[projectId]["path"])
        roadmap_path = project_path / ".auto-claude" / "roadmap.json"

        # Check if roadmap exists
        if not roadmap_path.exists():
            return {"success": False, "error": "Roadmap file not found"}

        # Load roadmap data
        roadmap = json.loads(roadmap_path.read_text())

        # Validate roadmap has features array
        if "features" not in roadmap:
            return {"success": False, "error": "Invalid roadmap structure: missing features array"}

        # Find the feature by ID
        feature_found = False
        for feature in roadmap["features"]:
            if feature.get("id") == featureId:
                # Validate status value
                valid_statuses = ["planned", "in_progress", "under_review", "completed", "cancelled"]
                if request.status not in valid_statuses:
                    return {
                        "success": False,
                        "error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
                    }

                # Update the feature status
                feature["status"] = request.status
                feature_found = True
                break

        if not feature_found:
            return {"success": False, "error": f"Feature {featureId} not found in roadmap"}

        # Update the roadmap's updatedAt timestamp
        from datetime import datetime, timezone
        roadmap["updatedAt"] = datetime.now(timezone.utc).isoformat()

        # Save the updated roadmap
        roadmap_path.parent.mkdir(parents=True, exist_ok=True)
        roadmap_path.write_text(json.dumps(roadmap, indent=2))

        # Set secure file permissions (owner read/write only)
        roadmap_path.chmod(0o600)

        return {"success": True}

    except json.JSONDecodeError as e:
        return {"success": False, "error": f"Invalid JSON in roadmap file: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/features/{featureId}/convert")
async def convert_feature_to_spec(projectId: str = Path(...), featureId: str = Path(...)):
    """Convert a roadmap feature to a task spec."""
    return {"success": True, "data": {"taskId": None}}


# ============================================
# Ideation Routes
# ============================================

ideation_router = APIRouter()


@ideation_router.get("")
async def get_ideation(projectId: str = Path(...)):
    """Get ideation data for a project."""
    from .projects import load_projects

    projects = load_projects()
    if projectId not in projects:
        return {"success": False, "error": f"Project {projectId} not found"}

    project_path = FilePath(projects[projectId]["path"])
    ideation_path = project_path / ".auto-claude" / "ideation.json"

    if not ideation_path.exists():
        return {"success": True, "data": None}

    try:
        ideation = json.loads(ideation_path.read_text())
        return {"success": True, "data": ideation}
    except Exception as e:
        return {"success": False, "error": str(e)}


@ideation_router.post("/generate")
async def generate_ideation(projectId: str = Path(...), request: IdeationConfig = ...):
    """
    Generate new ideas using AI.

    Starts an asynchronous ideation generation process using the ideation_runner.py CLI.
    The process analyzes the project context and generates ideas based on the specified types.

    Progress is broadcast via WebSocket events (ideation:progress, ideation:complete, ideation:error).
    """
    from ..services.ideation_service import get_ideation_service
    from .projects import load_projects

    # Validate project exists
    projects = load_projects()
    if projectId not in projects:
        return {"success": False, "error": f"Project {projectId} not found"}

    project_path = FilePath(projects[projectId]["path"])

    # Get ideation service
    service = get_ideation_service()

    # Check if already running
    if service.is_running(projectId):
        return {"success": False, "error": "Ideation generation is already running for this project"}

    # Start generation in background
    success = await service.start_generation(
        project_id=projectId,
        project_path=project_path,
        types=request.types,
        context=request.context,
        max_ideas=request.maxIdeas,
        refresh=False,  # generate appends to existing ideas
    )

    if not success:
        return {"success": False, "error": "Failed to start ideation generation"}

    return {"success": True, "message": "Ideation generation started"}


@ideation_router.post("/refresh")
async def refresh_ideation(projectId: str = Path(...), request: IdeationConfig = ...):
    """
    Refresh/regenerate ideas.

    Similar to generate_ideation but with refresh=True, which replaces existing ideas
    instead of appending to them. Useful when you want to regenerate ideas with updated
    project context or different configuration.

    Progress is broadcast via WebSocket events (ideation:progress, ideation:complete, ideation:error).
    """
    from ..services.ideation_service import get_ideation_service
    from .projects import load_projects

    # Validate project exists
    projects = load_projects()
    if projectId not in projects:
        return {"success": False, "error": f"Project {projectId} not found"}

    project_path = FilePath(projects[projectId]["path"])

    # Get ideation service
    service = get_ideation_service()

    # Check if already running
    if service.is_running(projectId):
        return {"success": False, "error": "Ideation generation is already running for this project"}

    # Start generation in background with refresh=True
    success = await service.start_generation(
        project_id=projectId,
        project_path=project_path,
        types=request.types,
        context=request.context,
        max_ideas=request.maxIdeas,
        refresh=True,  # refresh replaces existing ideas
    )

    if not success:
        return {"success": False, "error": "Failed to start ideation refresh"}

    return {"success": True, "message": "Ideation refresh started"}


@ideation_router.post("/stop")
async def stop_ideation(projectId: str = Path(...)):
    """
    Stop ongoing ideation generation.

    Cancels the background ideation generation process for the project.
    The process is terminated gracefully (SIGTERM), and if it doesn't respond
    within 5 seconds, it's forcefully killed (SIGKILL).

    Emits a WebSocket event (ideation:stopped) when cancelled.
    """
    from ..services.ideation_service import get_ideation_service

    # Get ideation service
    service = get_ideation_service()

    # Check if running
    if not service.is_running(projectId):
        return {"success": False, "error": "No ideation generation is running for this project"}

    # Stop the generation
    success = await service.stop_generation(projectId)

    if not success:
        return {"success": False, "error": "Failed to stop ideation generation"}

    return {"success": True, "message": "Ideation generation stopped"}


@ideation_router.patch("/ideas/{ideaId}")
async def update_idea_status(
    projectId: str = Path(...),
    ideaId: str = Path(...),
    request: IdeaStatusUpdate = ...
):
    """Update an idea's status in ideation.json."""
    from .projects import load_projects

    try:
        # Validate project exists
        projects = load_projects()
        if projectId not in projects:
            return {"success": False, "error": f"Project {projectId} not found"}

        # Get project path and ideation file
        project_path = FilePath(projects[projectId]["path"])
        ideation_path = project_path / ".auto-claude" / "ideation.json"

        # Check if ideation file exists
        if not ideation_path.exists():
            return {"success": False, "error": "Ideation file not found"}

        # Load ideation data
        ideation = json.loads(ideation_path.read_text())

        # Validate ideation has ideas array
        if "ideas" not in ideation:
            return {"success": False, "error": "Invalid ideation structure: missing ideas array"}

        # Find the idea by ID
        idea_found = False
        for idea in ideation["ideas"]:
            if idea.get("id") == ideaId:
                # Validate status value
                valid_statuses = ["new", "accepted", "rejected", "archived"]
                if request.status not in valid_statuses:
                    return {
                        "success": False,
                        "error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
                    }

                # Update the idea status
                idea["status"] = request.status
                idea_found = True
                break

        if not idea_found:
            return {"success": False, "error": f"Idea {ideaId} not found in ideation"}

        # Update the ideation's updatedAt timestamp if it exists
        from datetime import datetime, timezone
        if "updatedAt" in ideation:
            ideation["updatedAt"] = datetime.now(timezone.utc).isoformat()

        # Save the updated ideation
        ideation_path.parent.mkdir(parents=True, exist_ok=True)
        ideation_path.write_text(json.dumps(ideation, indent=2))

        # Set secure file permissions (owner read/write only)
        ideation_path.chmod(0o600)

        return {"success": True}

    except json.JSONDecodeError as e:
        return {"success": False, "error": f"Invalid JSON in ideation file: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@ideation_router.post("/ideas/{ideaId}/convert")
async def convert_idea_to_task(projectId: str = Path(...), ideaId: str = Path(...)):
    """Convert an idea to a task."""
    return {"success": True, "data": {"taskId": None}}


@ideation_router.post("/ideas/{ideaId}/dismiss")
async def dismiss_idea(projectId: str = Path(...), ideaId: str = Path(...)):
    """
    Dismiss an idea by setting its dismissed flag to true.

    This marks the idea as dismissed without changing its status or removing it from the list.
    Dismissed ideas can be filtered out in the UI but remain in the ideation.json file.
    """
    from .projects import load_projects

    try:
        # Validate project exists
        projects = load_projects()
        if projectId not in projects:
            return {"success": False, "error": f"Project {projectId} not found"}

        # Get project path and ideation file
        project_path = FilePath(projects[projectId]["path"])
        ideation_path = project_path / ".auto-claude" / "ideation.json"

        # Check if ideation file exists
        if not ideation_path.exists():
            return {"success": False, "error": "Ideation file not found"}

        # Load ideation data
        ideation = json.loads(ideation_path.read_text())

        # Validate ideation has ideas array
        if "ideas" not in ideation:
            return {"success": False, "error": "Invalid ideation structure: missing ideas array"}

        # Find the idea by ID and set dismissed flag
        idea_found = False
        for idea in ideation["ideas"]:
            if idea.get("id") == ideaId:
                # Set dismissed flag to true
                idea["dismissed"] = True
                idea_found = True
                break

        if not idea_found:
            return {"success": False, "error": f"Idea {ideaId} not found in ideation"}

        # Update the ideation's updatedAt timestamp if it exists
        from datetime import datetime, timezone
        if "updatedAt" in ideation:
            ideation["updatedAt"] = datetime.now(timezone.utc).isoformat()

        # Save the updated ideation
        ideation_path.parent.mkdir(parents=True, exist_ok=True)
        ideation_path.write_text(json.dumps(ideation, indent=2))

        # Set secure file permissions (owner read/write only)
        ideation_path.chmod(0o600)

        return {"success": True}

    except json.JSONDecodeError as e:
        return {"success": False, "error": f"Invalid JSON in ideation file: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@ideation_router.post("/dismiss-all")
async def dismiss_all_ideas(projectId: str = Path(...)):
    """
    Dismiss all ideas by setting their dismissed flag to true.

    This marks all ideas as dismissed without changing their status or removing them from the list.
    Dismissed ideas can be filtered out in the UI but remain in the ideation.json file.
    """
    from .projects import load_projects

    try:
        # Validate project exists
        projects = load_projects()
        if projectId not in projects:
            return {"success": False, "error": f"Project {projectId} not found"}

        # Get project path and ideation file
        project_path = FilePath(projects[projectId]["path"])
        ideation_path = project_path / ".auto-claude" / "ideation.json"

        # Check if ideation file exists
        if not ideation_path.exists():
            return {"success": False, "error": "Ideation file not found"}

        # Load ideation data
        ideation = json.loads(ideation_path.read_text())

        # Validate ideation has ideas array
        if "ideas" not in ideation:
            return {"success": False, "error": "Invalid ideation structure: missing ideas array"}

        # Count ideas before dismissing
        total_ideas = len(ideation["ideas"])

        if total_ideas == 0:
            return {
                "success": True,
                "message": "No ideas to dismiss",
                "dismissedCount": 0
            }

        # Set dismissed flag to true for all ideas
        for idea in ideation["ideas"]:
            idea["dismissed"] = True

        # Update the ideation's updatedAt timestamp if it exists
        from datetime import datetime, timezone
        if "updatedAt" in ideation:
            ideation["updatedAt"] = datetime.now(timezone.utc).isoformat()

        # Save the updated ideation
        ideation_path.parent.mkdir(parents=True, exist_ok=True)
        ideation_path.write_text(json.dumps(ideation, indent=2))

        # Set secure file permissions (owner read/write only)
        ideation_path.chmod(0o600)

        return {
            "success": True,
            "message": f"Successfully dismissed all {total_ideas} idea(s)",
            "dismissedCount": total_ideas
        }

    except json.JSONDecodeError as e:
        return {"success": False, "error": f"Invalid JSON in ideation file: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@ideation_router.post("/ideas/{ideaId}/archive")
async def archive_idea(projectId: str = Path(...), ideaId: str = Path(...)):
    """
    Archive an idea by setting its archived flag to true.

    This marks the idea as archived without changing its status or removing it from the list.
    Archived ideas can be filtered out in the UI but remain in the ideation.json file.
    """
    from .projects import load_projects

    try:
        # Validate project exists
        projects = load_projects()
        if projectId not in projects:
            return {"success": False, "error": f"Project {projectId} not found"}

        # Get project path and ideation file
        project_path = FilePath(projects[projectId]["path"])
        ideation_path = project_path / ".auto-claude" / "ideation.json"

        # Check if ideation file exists
        if not ideation_path.exists():
            return {"success": False, "error": "Ideation file not found"}

        # Load ideation data
        ideation = json.loads(ideation_path.read_text())

        # Validate ideation has ideas array
        if "ideas" not in ideation:
            return {"success": False, "error": "Invalid ideation structure: missing ideas array"}

        # Find the idea by ID and set archived flag
        idea_found = False
        for idea in ideation["ideas"]:
            if idea.get("id") == ideaId:
                # Set archived flag to true
                idea["archived"] = True
                idea_found = True
                break

        if not idea_found:
            return {"success": False, "error": f"Idea {ideaId} not found in ideation"}

        # Update the ideation's updatedAt timestamp if it exists
        from datetime import datetime, timezone
        if "updatedAt" in ideation:
            ideation["updatedAt"] = datetime.now(timezone.utc).isoformat()

        # Save the updated ideation
        ideation_path.parent.mkdir(parents=True, exist_ok=True)
        ideation_path.write_text(json.dumps(ideation, indent=2))

        # Set secure file permissions (owner read/write only)
        ideation_path.chmod(0o600)

        return {"success": True}

    except json.JSONDecodeError as e:
        return {"success": False, "error": f"Invalid JSON in ideation file: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@ideation_router.delete("/ideas/{ideaId}")
async def delete_idea(projectId: str = Path(...), ideaId: str = Path(...)):
    """
    Delete an idea by removing it from the ideation.json file.

    Unlike dismiss or archive which only set flags, this permanently removes the idea
    from the ideation data. This action cannot be undone.

    Args:
        projectId: The project ID containing the idea
        ideaId: The ID of the idea to delete

    Returns:
        success: True if the idea was deleted successfully
        error: Error message if the operation failed
    """
    from .projects import load_projects

    try:
        # Validate project exists
        projects = load_projects()
        if projectId not in projects:
            return {"success": False, "error": f"Project {projectId} not found"}

        # Get project path and ideation file
        project_path = FilePath(projects[projectId]["path"])
        ideation_path = project_path / ".auto-claude" / "ideation.json"

        # Check if ideation file exists
        if not ideation_path.exists():
            return {"success": False, "error": "Ideation file not found"}

        # Load ideation data
        ideation = json.loads(ideation_path.read_text())

        # Validate ideation has ideas array
        if "ideas" not in ideation:
            return {"success": False, "error": "Invalid ideation structure: missing ideas array"}

        # Find and remove the idea by ID
        original_count = len(ideation["ideas"])
        ideation["ideas"] = [idea for idea in ideation["ideas"] if idea.get("id") != ideaId]

        # Check if an idea was actually removed
        if len(ideation["ideas"]) == original_count:
            return {"success": False, "error": f"Idea {ideaId} not found in ideation"}

        # Update the ideation's updatedAt timestamp if it exists
        from datetime import datetime, timezone
        if "updatedAt" in ideation:
            ideation["updatedAt"] = datetime.now(timezone.utc).isoformat()

        # Save the updated ideation
        ideation_path.parent.mkdir(parents=True, exist_ok=True)
        ideation_path.write_text(json.dumps(ideation, indent=2))

        # Set secure file permissions (owner read/write only)
        ideation_path.chmod(0o600)

        return {"success": True}

    except json.JSONDecodeError as e:
        return {"success": False, "error": f"Invalid JSON in ideation file: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@ideation_router.post("/ideas/delete")
async def delete_multiple_ideas(projectId: str = Path(...), request: DeleteIdeasRequest = ...):
    """
    Delete multiple ideas by removing them from the ideation.json file.

    Unlike dismiss or archive which only set flags, this permanently removes the ideas
    from the ideation data. This action cannot be undone.

    Args:
        projectId: The project ID containing the ideas
        request: DeleteIdeasRequest with ideaIds array of IDs to delete

    Returns:
        success: True if ideas were deleted successfully
        deletedCount: Number of ideas that were actually deleted
        message: Success message
        error: Error message if the operation failed
    """
    from .projects import load_projects

    try:
        # Validate at least one idea ID is provided
        if not request.ideaIds or len(request.ideaIds) == 0:
            return {"success": False, "error": "At least one idea ID must be provided"}

        # Validate project exists
        projects = load_projects()
        if projectId not in projects:
            return {"success": False, "error": f"Project {projectId} not found"}

        # Get project path and ideation file
        project_path = FilePath(projects[projectId]["path"])
        ideation_path = project_path / ".auto-claude" / "ideation.json"

        # Check if ideation file exists
        if not ideation_path.exists():
            return {"success": False, "error": "Ideation file not found"}

        # Load ideation data
        ideation = json.loads(ideation_path.read_text())

        # Validate ideation has ideas array
        if "ideas" not in ideation:
            return {"success": False, "error": "Invalid ideation structure: missing ideas array"}

        # Count ideas before deletion
        original_count = len(ideation["ideas"])

        # Convert ideaIds to a set for efficient lookup
        idea_ids_to_delete = set(request.ideaIds)

        # Filter out ideas that should be deleted
        ideation["ideas"] = [idea for idea in ideation["ideas"] if idea.get("id") not in idea_ids_to_delete]

        # Calculate how many ideas were actually deleted
        deleted_count = original_count - len(ideation["ideas"])

        if deleted_count == 0:
            return {
                "success": False,
                "error": "None of the specified idea IDs were found in ideation"
            }

        # Update the ideation's updatedAt timestamp if it exists
        from datetime import datetime, timezone
        if "updatedAt" in ideation:
            ideation["updatedAt"] = datetime.now(timezone.utc).isoformat()

        # Save the updated ideation
        ideation_path.parent.mkdir(parents=True, exist_ok=True)
        ideation_path.write_text(json.dumps(ideation, indent=2))

        # Set secure file permissions (owner read/write only)
        ideation_path.chmod(0o600)

        return {
            "success": True,
            "deletedCount": deleted_count,
            "message": f"Successfully deleted {deleted_count} idea(s)"
        }

    except json.JSONDecodeError as e:
        return {"success": False, "error": f"Invalid JSON in ideation file: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
