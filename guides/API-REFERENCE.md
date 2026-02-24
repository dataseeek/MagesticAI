# API Reference Guide

This document provides a comprehensive reference for the Claude Code Manager Web REST API and WebSocket events. Use this guide for integration development, extension building, and understanding the backend architecture.

---

## Table of Contents

- [Overview](#overview)
- [Authentication](#authentication)
- [REST API Endpoints](#rest-api-endpoints)
  - [Health Check](#health-check)
  - [Projects API](#projects-api)
  - [Tasks API](#tasks-api)
  - [Task Execution API](#task-execution-api)
  - [Files API](#files-api)
  - [Terminals API](#terminals-api)
  - [Git API](#git-api)
  - [GitHub Integration API](#github-integration-api)
  - [GitLab Integration API](#gitlab-integration-api)
  - [Memory & Context API](#memory--context-api)
  - [Logs API](#logs-api)
  - [Settings API](#settings-api)
- [WebSocket Events](#websocket-events)
  - [Task Logs WebSocket](#task-logs-websocket)
  - [Progress WebSocket](#progress-websocket)
  - [Terminal WebSocket](#terminal-websocket)
  - [Events WebSocket](#events-websocket)
- [Data Models](#data-models)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)

---

## Overview

### Base URL

```
http://localhost:5000/api
```

When running with HTTPS:
```
https://localhost:5000/api
```

### API Conventions

- All endpoints return JSON responses
- Successful responses include `{ "success": true, "data": ... }`
- Error responses include `{ "success": false, "error": "message" }`
- All timestamps are in ISO 8601 format
- IDs are typically UUID strings

### Response Format

```json
{
  "success": true,
  "data": {
    // Response payload
  }
}
```

Error Response:
```json
{
  "success": false,
  "error": "Error message describing what went wrong"
}
```

---

## Authentication

Claude Code Manager Web uses token-based authentication via the `TokenAuthMiddleware`.

### Headers

Include the authorization token in requests:

```
Authorization: Bearer <your-token>
```

Or via query parameter for WebSocket connections:
```
ws://localhost:5000/ws/endpoint?token=<your-token>
```

### Excluded Paths

The following paths do not require authentication:
- `/api/health` - Health check endpoint
- Static files served under `/`

---

## REST API Endpoints

### Health Check

#### GET `/api/health`

Returns server health status. No authentication required.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

---

### Projects API

Base path: `/api/projects`

#### GET `/api/projects`

List all registered projects.

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "project-uuid",
      "name": "my-project",
      "path": "/path/to/project",
      "description": "Project description",
      "createdAt": "2024-01-15T10:30:00Z",
      "updatedAt": "2024-01-15T10:30:00Z"
    }
  ]
}
```

#### GET `/api/projects/{projectId}`

Get a specific project by ID.

**Parameters:**
- `projectId` (path) - Project UUID

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "project-uuid",
    "name": "my-project",
    "path": "/path/to/project",
    "description": "Project description"
  }
}
```

#### POST `/api/projects`

Register a new project.

**Request Body:**
```json
{
  "name": "my-project",
  "path": "/path/to/project",
  "description": "Optional description"
}
```

#### DELETE `/api/projects/{projectId}`

Remove a project from the manager (does not delete files).

---

### Tasks API

Base path: `/api/tasks`

#### GET `/api/projects/{projectId}/tasks`

List all tasks for a project.

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "task-uuid",
      "title": "Implement feature X",
      "status": "in-progress",
      "priority": "high",
      "phase": "coding",
      "createdAt": "2024-01-15T10:30:00Z"
    }
  ]
}
```

#### GET `/api/tasks/{taskId}`

Get a specific task with full details.

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "task-uuid",
    "title": "Implement feature X",
    "description": "Full task description",
    "status": "in-progress",
    "phase": "coding",
    "spec": { /* spec object */ },
    "plan": { /* implementation plan */ },
    "worktree": {
      "path": "/path/to/worktree",
      "branch": "task/feature-x"
    }
  }
}
```

#### POST `/api/projects/{projectId}/tasks`

Create a new task.

**Request Body:**
```json
{
  "title": "Implement feature X",
  "description": "Detailed description of the feature",
  "priority": "high",
  "labels": ["feature", "frontend"]
}
```

#### PATCH `/api/tasks/{taskId}`

Update a task.

**Request Body:**
```json
{
  "title": "Updated title",
  "status": "completed",
  "phase": "qa"
}
```

#### DELETE `/api/tasks/{taskId}`

Delete a task (including worktree cleanup).

---

### Task Execution API

Base path: `/api/tasks`

#### POST `/api/tasks/{taskId}/execute`

Start task execution with an AI agent.

**Request Body:**
```json
{
  "agentType": "coder",
  "subtaskId": "1.1",
  "model": "claude-sonnet-4-20250514"
}
```

**Agent Types:**
- `planner` - Plans implementation strategy
- `coder` - Implements code changes
- `qa` - Quality assurance and testing

#### POST `/api/tasks/{taskId}/cancel`

Cancel a running task execution.

#### GET `/api/tasks/{taskId}/status`

Get current execution status.

**Response:**
```json
{
  "success": true,
  "data": {
    "running": true,
    "agentType": "coder",
    "startedAt": "2024-01-15T10:30:00Z",
    "subtaskId": "1.1"
  }
}
```

---

### Files API

Base path: `/api/files`

#### GET `/api/files`

List directory contents.

**Query Parameters:**
- `path` (required) - Directory path to list
- `projectId` (optional) - Filter to project scope

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "name": "src",
      "path": "/project/src",
      "type": "directory",
      "size": 0
    },
    {
      "name": "package.json",
      "path": "/project/package.json",
      "type": "file",
      "size": 1234
    }
  ]
}
```

#### GET `/api/files/read`

Read file contents.

**Query Parameters:**
- `path` (required) - File path to read

**Response:**
```json
{
  "success": true,
  "data": {
    "content": "file contents here",
    "encoding": "utf-8"
  }
}
```

#### POST `/api/files/write`

Write file contents.

**Request Body:**
```json
{
  "path": "/project/src/file.ts",
  "content": "new file contents"
}
```

#### DELETE `/api/files`

Delete a file or directory.

**Query Parameters:**
- `path` (required) - Path to delete

---

### Terminals API

Base path: `/api/terminals`

#### GET `/api/terminals`

List all terminal sessions.

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "terminal-uuid",
      "title": "Terminal 1",
      "cwd": "/path/to/project",
      "running": true
    }
  ]
}
```

#### POST `/api/terminals`

Create a new terminal session.

**Request Body:**
```json
{
  "title": "My Terminal",
  "cwd": "/path/to/start",
  "cols": 120,
  "rows": 30
}
```

#### DELETE `/api/terminals/{terminalId}`

Close a terminal session.

#### POST `/api/terminals/{terminalId}/resize`

Resize terminal dimensions.

**Request Body:**
```json
{
  "cols": 150,
  "rows": 40
}
```

---

### Git API

Base path: `/api/git`

#### GET `/api/git/status`

Get git status for a path.

**Query Parameters:**
- `path` (required) - Repository path

**Response:**
```json
{
  "success": true,
  "data": {
    "branch": "main",
    "modified": ["src/file.ts"],
    "staged": [],
    "untracked": ["new-file.ts"],
    "ahead": 2,
    "behind": 0
  }
}
```

#### GET `/api/git/branches`

List all branches.

**Query Parameters:**
- `path` (required) - Repository path

#### GET `/api/git/worktrees`

List all git worktrees.

**Query Parameters:**
- `path` (required) - Repository path

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "path": "/project/.auto-claude/worktrees/task-123",
      "branch": "task/feature-x",
      "head": "abc123def",
      "prunable": false
    }
  ]
}
```

#### POST `/api/git/worktrees`

Create a new worktree.

**Request Body:**
```json
{
  "basePath": "/project",
  "branch": "task/feature-x",
  "worktreePath": "/project/.auto-claude/worktrees/task-123"
}
```

#### DELETE `/api/git/worktrees`

Remove a worktree.

**Query Parameters:**
- `path` (required) - Worktree path to remove

---

### GitHub Integration API

Base path: `/api/github`

#### GET `/api/github/cli/check`

Check if GitHub CLI (gh) is installed.

**Response:**
```json
{
  "success": true,
  "data": {
    "installed": true
  }
}
```

#### GET `/api/github/auth/check`

Check GitHub authentication status.

**Response:**
```json
{
  "success": true,
  "data": {
    "authenticated": true
  }
}
```

#### GET `/api/github/user`

Get authenticated GitHub username.

#### GET `/api/github/repos`

List user repositories.

**Response:**
```json
{
  "success": true,
  "data": {
    "repos": [
      {
        "name": "my-repo",
        "nameWithOwner": "user/my-repo",
        "description": "Repository description",
        "isPrivate": false,
        "url": "https://github.com/user/my-repo"
      }
    ]
  }
}
```

#### GET `/api/github/orgs`

List user organizations.

#### GET `/api/github/branches`

Get repository branches.

**Query Parameters:**
- `repo` (required) - Repository full name (owner/repo)
- `token` (required) - GitHub token

#### POST `/api/github/repos`

Create a new GitHub repository.

**Request Body:**
```json
{
  "repoName": "new-repo",
  "description": "Repository description",
  "private": false,
  "orgName": "optional-org"
}
```

#### GET `/api/github/detect-repo`

Detect GitHub remote for a local repository.

**Query Parameters:**
- `path` (required) - Local repository path

---

#### Project-specific GitHub Routes

Base path: `/api/projects/{projectId}/github`

#### GET `/api/projects/{projectId}/github/issues`

Get GitHub issues for the project.

**Query Parameters:**
- `state` (optional) - Filter by state: `open`, `closed`, `all`

#### GET `/api/projects/{projectId}/github/issues/{issueNumber}`

Get a specific GitHub issue.

#### GET `/api/projects/{projectId}/github/issues/{issueNumber}/comments`

Get comments for a GitHub issue.

#### POST `/api/projects/{projectId}/github/issues/{issueNumber}/investigate`

Investigate a GitHub issue using AI analysis.

**Request Body:**
```json
{
  "selectedCommentIds": [123, 456]
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "issue": { /* issue details */ },
    "comments": [ /* selected comments */ ],
    "analysis": {
      "status": "completed",
      "summary": "Brief summary of the issue",
      "issue_type": "bug",
      "complexity": "standard",
      "suggestions": ["Fix suggestion 1", "Fix suggestion 2"],
      "affected_areas": ["src/component.ts"],
      "risks": ["Breaking change risk"]
    }
  }
}
```

#### POST `/api/projects/{projectId}/github/import`

Import GitHub issues as tasks.

**Request Body:**
```json
{
  "issueNumbers": [1, 2, 3]
}
```

---

### GitLab Integration API

Base path: `/api/gitlab`

#### GET `/api/gitlab/cli/check`

Check if GitLab CLI (glab) is installed.

#### GET `/api/gitlab/auth/check`

Check GitLab authentication status.

**Query Parameters:**
- `hostname` (optional) - GitLab instance hostname

#### GET `/api/gitlab/user`

Get authenticated GitLab username.

#### GET `/api/gitlab/projects`

List user projects.

#### GET `/api/gitlab/groups`

List user groups.

#### POST `/api/gitlab/projects`

Create a new GitLab project.

**Request Body:**
```json
{
  "projectName": "new-project",
  "description": "Project description",
  "visibility": "private",
  "groupId": 123
}
```

---

#### Project-specific GitLab Routes

Base path: `/api/projects/{projectId}/gitlab`

#### GET `/api/projects/{projectId}/gitlab/issues`

Get GitLab issues for the project.

#### POST `/api/projects/{projectId}/gitlab/issues/{issueIid}/investigate`

Investigate a GitLab issue using AI analysis.

**Request Body:**
```json
{
  "selectedNoteIds": [123, 456]
}
```

---

#### Merge Request Routes

Base path: `/api/projects/{projectId}/gitlab/merge-requests`

#### GET `/api/projects/{projectId}/gitlab/merge-requests`

List merge requests for the project.

**Query Parameters:**
- `state` (optional) - Filter by state: `opened`, `closed`, `merged`, `all`

#### GET `/api/projects/{projectId}/gitlab/merge-requests/{mrIid}`

Get a specific merge request.

#### POST `/api/projects/{projectId}/gitlab/merge-requests`

Create a new merge request.

**Request Body:**
```json
{
  "sourceBranch": "feature-branch",
  "targetBranch": "main",
  "title": "Add new feature",
  "description": "Feature description"
}
```

#### PATCH `/api/projects/{projectId}/gitlab/merge-requests/{mrIid}`

Update a merge request.

**Request Body:**
```json
{
  "title": "Updated title",
  "description": "Updated description",
  "labels": ["feature", "urgent"]
}
```

#### PATCH `/api/projects/{projectId}/gitlab/merge-requests/{mrIid}/assign`

Assign users to a merge request.

**Request Body:**
```json
{
  "userIds": [1, 2, 3]
}
```

#### POST `/api/projects/{projectId}/gitlab/merge-requests/{mrIid}/approve`

Approve a merge request.

#### POST `/api/projects/{projectId}/gitlab/merge-requests/{mrIid}/merge`

Merge a merge request.

**Request Body:**
```json
{
  "mergeMethod": "squash"
}
```

**Merge Methods:**
- `merge` - Standard merge (default)
- `squash` - Squash commits
- `rebase` - Rebase before merge

#### POST `/api/projects/{projectId}/gitlab/merge-requests/{mrIid}/notes`

Post a comment on a merge request.

**Request Body:**
```json
{
  "body": "Comment text in markdown"
}
```

---

#### MR Code Review Routes

#### POST `/api/projects/{projectId}/gitlab/merge-requests/{mrIid}/review/run`

Run AI-powered code review on a merge request.

**Response:**
```json
{
  "success": true,
  "data": {
    "merge_request": { /* MR metadata */ },
    "review": {
      "status": "completed",
      "summary": "Review summary",
      "review_status": "needs_work",
      "code_quality": "good",
      "findings": [
        {
          "severity": "major",
          "category": "bug",
          "file": "src/component.ts",
          "line": 42,
          "message": "Potential null reference",
          "suggestion": "Add null check"
        }
      ],
      "security_concerns": ["SQL injection risk"],
      "performance_notes": ["Consider caching"],
      "test_coverage": "Tests need updating"
    }
  }
}
```

#### POST `/api/projects/{projectId}/gitlab/merge-requests/{mrIid}/review/followup`

Run follow-up AI review with additional context.

**Request Body:**
```json
{
  "additionalContext": "Can you explain the security implications?",
  "previousReview": { /* previous review data */ },
  "focusAreas": ["security", "performance"]
}
```

#### POST `/api/projects/{projectId}/gitlab/merge-requests/{mrIid}/review/post`

Post review findings as comments on the MR.

**Request Body:**
```json
{
  "selectedFindingIds": ["finding-1", "finding-2"],
  "reviewFindings": { /* review data */ }
}
```

#### POST `/api/projects/{projectId}/gitlab/merge-requests/{mrIid}/review/cancel`

Cancel an ongoing review (informational - reviews are synchronous).

---

### Memory & Context API

Base path: `/api/memory`

#### GET `/api/memory/infrastructure`

Get memory infrastructure status.

**Query Parameters:**
- `dbPath` (optional) - Custom database path

**Response:**
```json
{
  "success": true,
  "data": {
    "kuzuInstalled": false,
    "databasePath": "/home/user/.auto-claude/memories",
    "databaseExists": true,
    "databases": [],
    "ready": true
  }
}
```

#### GET `/api/memory/databases`

List available memory databases.

#### POST `/api/memory/test-connection`

Test connection to memory database.

**Request Body:**
```json
{
  "dbPath": "/path/to/db",
  "database": "memory_db"
}
```

#### POST `/api/memory/validate-api-key`

Validate an LLM provider API key.

**Request Body:**
```json
{
  "provider": "openai",
  "apiKey": "sk-..."
}
```

#### POST `/api/memory/test-graphiti`

Test Graphiti memory system connection.

**Request Body:**
```json
{
  "embeddingProvider": "openai",
  "embeddingModel": "text-embedding-3-small",
  "openaiApiKey": "sk-...",
  "database": "memory_db",
  "dbPath": "/path/to/db"
}
```

---

#### Project Context Routes

Base path: `/api/projects/{projectId}`

#### GET `/api/projects/{projectId}/context`

Get project context including index and memories.

**Response:**
```json
{
  "success": true,
  "data": {
    "projectIndex": { /* index data */ },
    "memoryStatus": {
      "enabled": true,
      "available": true,
      "sessionInsightsCount": 5,
      "graphitiAvailable": true
    },
    "recentMemories": [
      {
        "id": "spec-id:session_1",
        "specId": "spec-id",
        "sessionNumber": 1,
        "timestamp": "2024-01-15T10:30:00Z",
        "type": "session_insight",
        "content": "Summary text"
      }
    ]
  }
}
```

#### POST `/api/projects/{projectId}/context/refresh`

Refresh/regenerate project index.

#### GET `/api/projects/{projectId}/memory/status`

Get memory system status for project.

#### GET `/api/projects/{projectId}/memory/search`

Search project memories.

**Query Parameters:**
- `q` (required) - Search query

#### GET `/api/projects/{projectId}/memory/recent`

Get recent memories.

**Query Parameters:**
- `limit` (optional) - Number of results (default: 10)

#### GET `/api/projects/{projectId}/env`

Get project environment configuration.

**Response:**
```json
{
  "success": true,
  "data": {
    "claudeAuthStatus": "authenticated",
    "linearEnabled": false,
    "githubEnabled": true,
    "gitlabEnabled": false,
    "graphitiEnabled": false,
    "enableFancyUi": true
  }
}
```

#### PATCH `/api/projects/{projectId}/env`

Update project environment configuration.

**Request Body:**
```json
{
  "linearApiKey": "lin_api_...",
  "githubToken": "ghp_...",
  "gitlabToken": "glpat-...",
  "graphitiEnabled": true,
  "enableFancyUi": true,
  "claudeToken": "..."
}
```

#### GET `/api/projects/{projectId}/claude-auth`

Check Claude authentication status.

#### POST `/api/projects/{projectId}/claude-setup`

Check Claude CLI status and get setup instructions.

---

#### Linear Integration Routes

Base path: `/api/projects/{projectId}/linear`

#### GET `/api/projects/{projectId}/linear/teams`

Get Linear teams.

#### GET `/api/projects/{projectId}/linear/projects`

Get Linear projects for a team.

**Query Parameters:**
- `teamId` (required) - Linear team ID

#### GET `/api/projects/{projectId}/linear/issues`

Get Linear issues.

**Query Parameters:**
- `teamId` (optional) - Filter by team
- `projectId` (optional) - Filter by project

#### POST `/api/projects/{projectId}/linear/import`

Import Linear issues as tasks.

**Request Body:**
```json
{
  "issueIds": ["issue-uuid-1", "issue-uuid-2"]
}
```

#### GET `/api/projects/{projectId}/linear/status`

Check Linear connection status.

---

### Logs API

Base path: `/api/logs`

#### GET `/api/logs`

List all available log files.

**Response:**
```json
{
  "files": [
    {
      "name": "server",
      "filename": "server.log",
      "path": "/path/to/logs/server.log",
      "exists": true,
      "size": 12345,
      "size_human": "12.1 KB"
    }
  ],
  "log_dir": "/path/to/logs"
}
```

#### GET `/api/logs/{log_type}`

Get recent log entries.

**Path Parameters:**
- `log_type` - Log type: `server`, `errors`, `agent`, `frontend`

**Query Parameters:**
- `lines` (optional) - Number of lines (default: 100, max: 10000)
- `level` (optional) - Filter by level: `DEBUG`, `INFO`, `WARNING`, `ERROR`

**Response:**
```json
{
  "entries": [
    {
      "timestamp": "2024-01-15T10:30:00Z",
      "level": "INFO",
      "logger": "server.main",
      "message": "Server started",
      "raw": "2024-01-15 10:30:00 INFO server.main Server started"
    }
  ],
  "total": 100,
  "log_type": "server",
  "log_file": "/path/to/server.log"
}
```

#### GET `/api/logs/{log_type}/raw`

Get raw log file content as plain text.

#### GET `/api/logs/{log_type}/download`

Download a log file.

#### DELETE `/api/logs/{log_type}`

Clear a specific log file.

#### DELETE `/api/logs`

Clear all log files.

#### POST `/api/logs/frontend`

Receive log entries from the frontend.

**Request Body:**
```json
{
  "entries": [
    {
      "timestamp": "2024-01-15T10:30:00Z",
      "level": "error",
      "category": "API",
      "message": "Request failed",
      "data": { "url": "/api/tasks" },
      "stack": "Error stack trace..."
    }
  ]
}
```

---

### Settings API

Base path: `/api/settings`

#### GET `/api/settings`

Get application settings.

#### PATCH `/api/settings`

Update application settings.

---

## WebSocket Events

### Task Logs WebSocket

#### Endpoint: `/ws/tasks/{task_id}/logs`

Stream real-time logs from a specific task.

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:5000/ws/tasks/task-uuid/logs?token=...');
```

**Messages Received:**

Connection acknowledgment:
```json
{
  "type": "connected",
  "task_id": "task-uuid",
  "message": "Connected to log stream"
}
```

Log entry:
```json
{
  "type": "log",
  "task_id": "task-uuid",
  "content": "Log message content",
  "timestamp": "2024-01-15T10:30:00.123Z",
  "level": "info",
  "source": "agent"
}
```

Heartbeat (sent every 30 seconds):
```json
{
  "type": "heartbeat"
}
```

**Log Levels:** `debug`, `info`, `warning`, `error`

**Log Sources:** `agent`, `stdout`, `stderr`

---

#### Endpoint: `/ws/logs`

Stream logs from ALL running tasks.

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:5000/ws/logs?token=...');
```

**Messages:** Same format as task-specific logs.

---

### Progress WebSocket

#### Endpoint: `/ws/tasks/{task_id}/progress`

Stream task execution progress updates.

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:5000/ws/tasks/task-uuid/progress?token=...');
```

**Messages Received:**

Progress update:
```json
{
  "type": "progress",
  "task_id": "task-uuid",
  "phase": "coding",
  "subtask_id": "1.1",
  "status": "in_progress",
  "message": "Implementing feature...",
  "percentage": 45
}
```

Completion:
```json
{
  "type": "completed",
  "task_id": "task-uuid",
  "result": {
    "success": true,
    "files_changed": ["src/file.ts"]
  }
}
```

Error:
```json
{
  "type": "error",
  "task_id": "task-uuid",
  "error": "Error message"
}
```

---

### Terminal WebSocket

#### Endpoint: `/ws/terminals/{terminal_id}`

Full-duplex PTY terminal connection.

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:5000/ws/terminals/term-uuid?token=...');
```

**Messages Sent (Client → Server):**

Terminal input:
```json
{
  "type": "input",
  "data": "ls -la\r"
}
```

Resize terminal:
```json
{
  "type": "resize",
  "cols": 120,
  "rows": 40
}
```

**Messages Received (Server → Client):**

Terminal output:
```json
{
  "type": "output",
  "data": "file1.txt  file2.txt\n"
}
```

Terminal closed:
```json
{
  "type": "exit",
  "code": 0
}
```

---

### Events WebSocket

#### Endpoint: `/ws/events`

General event stream for application-wide events.

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:5000/ws/events?token=...');
```

**Messages Received:**

Task status change:
```json
{
  "type": "task_status_changed",
  "task_id": "task-uuid",
  "old_status": "pending",
  "new_status": "in_progress"
}
```

Task created:
```json
{
  "type": "task_created",
  "task": { /* task object */ }
}
```

Task deleted:
```json
{
  "type": "task_deleted",
  "task_id": "task-uuid"
}
```

Project updated:
```json
{
  "type": "project_updated",
  "project_id": "project-uuid"
}
```

---

## Data Models

### Task Status Values

| Status | Description |
|--------|-------------|
| `pending` | Task created, not yet started |
| `planning` | Planner agent is creating implementation plan |
| `in-progress` | Coder agent is implementing |
| `qa` | QA agent is reviewing/testing |
| `review` | Awaiting human review |
| `completed` | Task successfully completed |
| `failed` | Task execution failed |
| `cancelled` | Task was cancelled |

### Task Phase Values

| Phase | Description |
|-------|-------------|
| `spec` | Specification creation |
| `planning` | Implementation planning |
| `coding` | Code implementation |
| `qa` | Quality assurance |
| `merge` | Ready for merge |

### Agent Types

| Type | Description |
|------|-------------|
| `planner` | Creates implementation plans from specs |
| `coder` | Implements code changes |
| `qa` | Reviews code and runs tests |

### Issue/Review Types

| Type | Description |
|------|-------------|
| `bug` | Something is broken |
| `feature` | New functionality |
| `documentation` | Docs update needed |
| `refactor` | Code restructuring |
| `performance` | Performance improvement |
| `security` | Security concern |
| `other` | Other category |

### Complexity Levels

| Level | Description |
|-------|-------------|
| `simple` | Single file, clear fix, < 1 hour |
| `standard` | Multiple files, 1-4 hours |
| `complex` | Architectural changes, > 4 hours |

### Review Severity

| Severity | Description |
|----------|-------------|
| `critical` | Must fix - security, bugs, data loss |
| `major` | Should fix - significant issues |
| `minor` | Nice to fix - style, small improvements |
| `suggestion` | Optional improvements |

---

## Error Handling

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request - Invalid parameters |
| 401 | Unauthorized - Invalid or missing token |
| 404 | Not Found - Resource doesn't exist |
| 500 | Internal Server Error |

### Error Response Format

```json
{
  "success": false,
  "error": "Human-readable error message",
  "detail": "Optional technical details"
}
```

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "Project not found" | Invalid project ID | Verify project exists |
| "Task not found" | Invalid task ID | Verify task exists |
| "GitHub CLI not installed" | gh not available | Install GitHub CLI |
| "Not authenticated" | Missing/invalid token | Check authentication |
| "Command timed out" | CLI operation too slow | Retry or check connectivity |

---

## Rate Limiting

Currently, Claude Code Manager Web does not implement rate limiting. For production deployments, consider adding rate limiting middleware.

Recommended limits for high-usage scenarios:
- API requests: 100 requests per minute per client
- WebSocket connections: 10 concurrent per client
- File operations: 50 per minute per client

---

## Example Usage

### JavaScript/TypeScript Client

```typescript
// API Request
const response = await fetch('http://localhost:5000/api/projects', {
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
});
const data = await response.json();

// WebSocket Connection
const ws = new WebSocket(`ws://localhost:5000/ws/tasks/${taskId}/logs?token=${token}`);
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  if (message.type === 'log') {
    console.log(`[${message.level}] ${message.content}`);
  }
};
```

### Python Client

```python
import requests
import websockets
import asyncio

# API Request
headers = {'Authorization': f'Bearer {token}'}
response = requests.get('http://localhost:5000/api/projects', headers=headers)
data = response.json()

# WebSocket Connection
async def stream_logs(task_id, token):
    uri = f'ws://localhost:5000/ws/tasks/{task_id}/logs?token={token}'
    async with websockets.connect(uri) as ws:
        async for message in ws:
            data = json.loads(message)
            if data['type'] == 'log':
                print(f"[{data['level']}] {data['content']}")

asyncio.run(stream_logs('task-uuid', token))
```

### cURL Examples

```bash
# List projects
curl -H "Authorization: Bearer $TOKEN" http://localhost:5000/api/projects

# Create a task
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "Implement feature", "description": "Details..."}' \
  http://localhost:5000/api/projects/PROJECT_ID/tasks

# Start task execution
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"agentType": "coder", "subtaskId": "1.1"}' \
  http://localhost:5000/api/tasks/TASK_ID/execute
```

---

**Claude Code Manager Web** - Comprehensive API for AI-powered coding task management.
