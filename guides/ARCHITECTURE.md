# MagesticAI - Architecture Guide

This guide provides a comprehensive overview of the MagesticAI architecture, including system design, data flow, component interactions, and key design decisions.

---

## Table of Contents

1. [Overview](#overview)
2. [High-Level Architecture](#high-level-architecture)
3. [System Layers](#system-layers)
4. [Frontend Architecture](#frontend-architecture)
5. [Web Server Architecture](#web-server-architecture)
6. [Backend Agent Architecture](#backend-agent-architecture)
7. [Data Flow](#data-flow)
8. [Communication Protocols](#communication-protocols)
9. [Storage Architecture](#storage-architecture)
10. [Security Architecture](#security-architecture)
11. [Key Design Decisions](#key-design-decisions)
12. [Scalability Considerations](#scalability-considerations)

---

## Overview

MagesticAI is a **three-tier web application** that orchestrates AI-powered coding tasks through a coordination of autonomous agents. The system is designed for:

- **Browser-based access** - Full functionality from any modern web browser
- **Real-time interaction** - Live updates via WebSocket connections
- **AI agent orchestration** - Coordinated Planner, Coder, and QA agents
- **Isolated task execution** - Git worktrees for safe, parallel task development

### Architecture Principles

| Principle | Description |
|-----------|-------------|
| **Separation of Concerns** | Frontend, API server, and agent system are decoupled |
| **Event-Driven** | Real-time updates via WebSocket event broadcasting |
| **Stateless API** | REST API with token-based authentication |
| **File-Based Storage** | No external database dependencies (uses JSON files) |
| **Process Isolation** | Agents run as separate subprocess for stability |

---

## High-Level Architecture

```
                                 ┌─────────────────────────────────────┐
                                 │         Browser Client               │
                                 │  ┌─────────────────────────────────┐ │
                                 │  │     React 19 + Vite + TS        │ │
                                 │  │  ┌──────────┐ ┌──────────────┐  │ │
                                 │  │  │ Zustand  │ │   Monaco     │  │ │
                                 │  │  │  Stores  │ │   Editor     │  │ │
                                 │  │  └──────────┘ └──────────────┘  │ │
                                 │  │  ┌──────────┐ ┌──────────────┐  │ │
                                 │  │  │ xterm.js │ │  @dnd-kit    │  │ │
                                 │  │  │ Terminal │ │  Kanban      │  │ │
                                 │  │  └──────────┘ └──────────────┘  │ │
                                 │  └─────────────────────────────────┘ │
                                 └───────────────┬─────────────────────┘
                                                 │
                         ┌───────────────────────┼───────────────────────┐
                         │        HTTP/REST      │      WebSocket        │
                         │       Port 5173       │      Port 5173        │
                         │      (Vite Proxy)     │     (Vite Proxy)      │
                         └───────────────────────┼───────────────────────┘
                                                 │
                                                 ▼
                                 ┌─────────────────────────────────────┐
                                 │         Web Server (FastAPI)         │
                                 │              Port 8000               │
                                 │  ┌─────────────────────────────────┐ │
                                 │  │         REST API Routes         │ │
                                 │  │  /api/projects  /api/tasks      │ │
                                 │  │  /api/files     /api/terminals  │ │
                                 │  └─────────────────────────────────┘ │
                                 │  ┌─────────────────────────────────┐ │
                                 │  │      WebSocket Handlers         │ │
                                 │  │  /ws/events    /ws/terminal     │ │
                                 │  │  /ws/tasks/*/progress           │ │
                                 │  └─────────────────────────────────┘ │
                                 │  ┌─────────────────────────────────┐ │
                                 │  │  PTY Manager  │  Agent Service  │ │
                                 │  └─────────────────────────────────┘ │
                                 └───────────────┬─────────────────────┘
                                                 │
                         ┌───────────────────────┼───────────────────────┐
                         │      Subprocess       │       File I/O        │
                         │      Execution        │      Operations       │
                         └───────────────────────┼───────────────────────┘
                                                 │
                                                 ▼
                                 ┌─────────────────────────────────────┐
                                 │      Backend Agents (Python)         │
                                 │  ┌─────────────────────────────────┐ │
                                 │  │      Claude Agent SDK           │ │
                                 │  │  ┌─────────┐  ┌─────────────┐   │ │
                                 │  │  │ Planner │  │    Coder    │   │ │
                                 │  │  │  Agent  │  │    Agent    │   │ │
                                 │  │  └─────────┘  └─────────────┘   │ │
                                 │  │  ┌─────────┐  ┌─────────────┐   │ │
                                 │  │  │   QA    │  │  QA Fixer   │   │ │
                                 │  │  │Reviewer │  │    Agent    │   │ │
                                 │  │  └─────────┘  └─────────────┘   │ │
                                 │  └─────────────────────────────────┘ │
                                 │  ┌─────────────────────────────────┐ │
                                 │  │  Graphiti Memory (LadybugDB)    │ │
                                 │  └─────────────────────────────────┘ │
                                 └─────────────────────────────────────┘
                                                 │
                                                 ▼
                                 ┌─────────────────────────────────────┐
                                 │         File System Storage          │
                                 │  ┌─────────────────────────────────┐ │
                                 │  │  ~/.magestic-ai/            │ │
                                 │  │  ├── projects.json              │ │
                                 │  │  ├── settings.json              │ │
                                 │  │  └── .token                     │ │
                                 │  └─────────────────────────────────┘ │
                                 │  ┌─────────────────────────────────┐ │
                                 │  │  project/.magestic-ai/          │ │
                                 │  │  ├── specs/{task-id}/           │ │
                                 │  │  └── worktrees/tasks/           │ │
                                 │  └─────────────────────────────────┘ │
                                 └─────────────────────────────────────┘
```

---

## System Layers

MagesticAI consists of four distinct layers:

### Layer 1: Presentation Layer (Frontend)

| Component | Technology | Responsibility |
|-----------|------------|----------------|
| **UI Framework** | React 19 | Component rendering, state management |
| **Build Tool** | Vite 7 | Development server, HMR, bundling |
| **Styling** | Tailwind CSS 4 | Utility-first CSS framework |
| **State** | Zustand | Global state management |
| **Terminals** | xterm.js | Browser-based terminal emulation |
| **Editor** | Monaco Editor | Code editing with syntax highlighting |

### Layer 2: API Layer (Web Server)

| Component | Technology | Responsibility |
|-----------|------------|----------------|
| **Framework** | FastAPI | REST API endpoints |
| **Server** | Uvicorn | ASGI server with WebSocket support |
| **Validation** | Pydantic v2 | Request/response validation |
| **PTY** | ptyprocess | Terminal session management |
| **Git** | GitPython | Repository operations |

### Layer 3: Business Logic Layer (Backend Agents)

| Component | Technology | Responsibility |
|-----------|------------|----------------|
| **SDK** | Claude Agent SDK | AI agent orchestration |
| **Planner** | Python | Creates implementation plans |
| **Coder** | Python | Implements code changes |
| **QA** | Python | Code review and validation |
| **Memory** | Graphiti + LadybugDB | Knowledge graph storage |

### Layer 4: Storage Layer

| Component | Technology | Responsibility |
|-----------|------------|----------------|
| **App Data** | JSON files | User settings, project list |
| **Task Data** | JSON + Markdown | Specs, plans, logs |
| **Git Worktrees** | Git | Isolated task branches |
| **Memory** | LadybugDB | Embedded graph database |

---

## Frontend Architecture

The frontend follows a **component-based architecture** with centralized state management.

### Component Hierarchy

```
App.tsx
├── LoginPage.tsx                    # Authentication
└── MainLayout
    ├── Sidebar.tsx                  # Navigation sidebar
    │   ├── ProjectSelector
    │   └── ViewNavigation
    │
    ├── ProjectTabBar.tsx            # Multi-project tabs
    │
    └── ViewRouter                   # Dynamic view rendering
        ├── KanbanBoard.tsx          # Task management
        │   ├── KanbanColumn.tsx
        │   └── TaskCard.tsx
        │
        ├── TerminalGrid.tsx         # Multi-terminal view
        │   └── Terminal.tsx
        │       └── xterm.js instance
        │
        ├── EditorPage.tsx           # Code editor
        │   ├── FileExplorer.tsx
        │   └── MonacoEditor
        │
        ├── Worktrees.tsx            # Git worktree management
        ├── Roadmap.tsx              # AI roadmap generation
        ├── Ideation.tsx             # AI ideation
        ├── Context.tsx              # Project context/memory
        ├── Changelog.tsx            # Changelog generation
        ├── Insights.tsx             # AI insights
        ├── GitHubIssues.tsx         # GitHub integration
        └── GitLabIssues.tsx         # GitLab integration
```

### State Management Architecture

The frontend uses **Zustand** for state management with multiple specialized stores:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Zustand Store Architecture                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────┐  │
│  │  useProjectStore │  │   useTaskStore   │  │ useAuthStore  │  │
│  │  - projects[]    │  │  - tasks[]       │  │ - token       │  │
│  │  - activeProject │  │  - selectedTask  │  │ - isAuth      │  │
│  │  - openTabs[]    │  │  - execution     │  │               │  │
│  └──────────────────┘  └──────────────────┘  └───────────────┘  │
│                                                                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────┐  │
│  │ useTerminalStore │  │ useSettingsStore │  │useContextStore│  │
│  │  - terminals[]   │  │  - settings      │  │ - memories[]  │  │
│  │  - activeId      │  │  - language      │  │ - indexed     │  │
│  │  - history       │  │  - theme         │  │               │  │
│  └──────────────────┘  └──────────────────┘  └───────────────┘  │
│                                                                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────┐  │
│  │ useRoadmapStore  │  │ useIdeationStore │  │useInsightsStoe│  │
│  │  - roadmap       │  │  - ideas[]       │  │ - messages[]  │  │
│  │  - isGenerating  │  │  - filters       │  │ - loading     │  │
│  └──────────────────┘  └──────────────────┘  └───────────────┘  │
│                                                                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────┐  │
│  │useChangelogStore │  │  useGitHubStore  │  │ useGitLabStore│  │
│  │  - entries[]     │  │  - issues[]      │  │ - issues[]    │  │
│  │  - isGenerating  │  │  - prs[]         │  │ - mrs[]       │  │
│  └──────────────────┘  └──────────────────┘  └───────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### API Communication Pattern

The frontend uses an **adapter pattern** to abstract API communication:

```typescript
// apps/frontend-web/src/lib/api-adapter.ts

// Web API interface - unified access point
window.API = {
  // Projects
  getProjects: () => api.get('/api/projects'),
  createProject: (data) => api.post('/api/projects', data),
  updateProject: (id, data) => api.put(`/api/projects/${id}`, data),
  deleteProject: (id) => api.delete(`/api/projects/${id}`),

  // Tasks
  getTasks: (projectId) => api.get(`/api/projects/${projectId}/tasks`),
  createTask: (projectId, data) => api.post(`/api/projects/${projectId}/tasks`, data),
  startTask: (taskId, options) => api.post(`/api/tasks/${taskId}/start`, options),
  stopTask: (taskId) => api.post(`/api/tasks/${taskId}/stop`),

  // Terminals
  createTerminal: (cwd) => api.post('/api/terminals', { cwd }),
  closeTerminal: (id) => api.delete(`/api/terminals/${id}`),

  // ... 50+ methods
};
```

### WebSocket Integration

Real-time updates flow through a centralized WebSocket manager:

```
┌──────────────────────────────────────────────────────────────────┐
│                   WebSocket Event Flow                            │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│   Frontend                    WebSocket                 Backend   │
│   ────────                    ─────────                 ───────   │
│                                                                   │
│   WebSocketManager ──────────► /ws/events ◄───────── Event Bus   │
│        │                           │                              │
│        │  onMessage()              │                              │
│        ▼                           │                              │
│   Event Router                     │                              │
│        │                           │                              │
│        ├─► task:status ──► useTaskStore.updateTask()             │
│        ├─► task:progress ─► useTaskStore.setProgress()           │
│        ├─► task:log ──────► useTaskStore.addLog()                │
│        └─► task:error ────► useTaskStore.setError()              │
│                                                                   │
│   Terminal.tsx ───────────► /ws/terminal/{id} ◄───── PTYSession  │
│        │                           │                              │
│        ├─► send(input)             │                              │
│        └◄─ receive(output)         │                              │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

---

## Web Server Architecture

The web server acts as the **orchestration layer** between the frontend and backend agents.

### Request Processing Flow

```
                    HTTP Request
                         │
                         ▼
            ┌────────────────────────┐
            │    CORS Middleware     │
            │   (Allowed Origins)    │
            └────────────────────────┘
                         │
                         ▼
            ┌────────────────────────┐
            │   Token Auth Check     │
            │  (Authorization Header)│
            └────────────────────────┘
                         │
                         ▼
            ┌────────────────────────┐
            │     Route Handler      │
            │   (FastAPI Router)     │
            └────────────────────────┘
                         │
          ┌──────────────┴──────────────┐
          ▼                              ▼
┌──────────────────┐          ┌──────────────────┐
│  File Operations │          │  Agent Service   │
│  - Read/Write    │          │  - Start Task    │
│  - List/Search   │          │  - Stop Task     │
└──────────────────┘          │  - Get Status    │
                              └──────────────────┘
                                       │
                                       ▼
                              ┌──────────────────┐
                              │   Subprocess     │
                              │ (Python Agent)   │
                              └──────────────────┘
```

### Key Services

#### Agent Service (`services/agent_service.py`)

Manages the lifecycle of AI agent execution:

```python
class AgentService:
    """Orchestrates agent subprocess execution."""

    def __init__(self):
        self.running_tasks: dict[str, Process] = {}
        self.callbacks: dict[str, list[Callable]] = {}

    async def start_task(self, task_id: str, options: StartTaskOptions) -> None:
        """
        Starts task execution as a subprocess.

        Flow:
        1. Validate task exists and is in valid state
        2. Create/switch to git worktree
        3. Spawn Python subprocess with agent runner
        4. Register progress callbacks
        5. Return immediately (async execution)
        """

    async def stop_task(self, task_id: str) -> None:
        """Terminates running task subprocess."""

    def get_task_status(self, task_id: str) -> TaskStatus:
        """Returns current execution status."""

    def register_callback(self, task_id: str, callback: Callable) -> None:
        """Register for progress/completion events."""
```

#### PTY Manager (`pty/manager.py`)

Handles browser-based terminal sessions:

```python
class PTYManager:
    """Manages pseudo-terminal sessions for web clients."""

    sessions: dict[str, PTYSession] = {}

    def create_session(self, cwd: str, env: dict) -> str:
        """
        Creates new PTY session.

        Returns: session_id for WebSocket connection
        """

    def get_session(self, session_id: str) -> PTYSession:
        """Retrieves active session."""

    def write_to_session(self, session_id: str, data: bytes) -> None:
        """Sends input to PTY."""

    def read_from_session(self, session_id: str) -> bytes:
        """Reads output from PTY."""

    def resize_session(self, session_id: str, cols: int, rows: int) -> None:
        """Resizes terminal dimensions."""

    def close_session(self, session_id: str) -> None:
        """Terminates and cleans up session."""
```

### Route Organization

```
apps/web-server/server/routes/
├── projects.py       # /api/projects - Project CRUD
├── tasks.py          # /api/tasks - Task management
├── execution.py      # /api/tasks/{id}/start|stop - Task execution
├── files.py          # /api/files - File operations
├── terminal.py       # /api/terminals - Terminal management
├── settings.py       # /api/settings - App settings
├── git.py            # /api/git - Git operations
├── github.py         # /api/github - GitHub integration
├── gitlab.py         # /api/gitlab - GitLab integration
├── context.py        # /api/memory - Project context/memory
├── roadmap.py        # /api/projects/{id}/roadmap - Roadmap generation
├── changelog.py      # /api/projects/{id}/changelog - Changelog
└── logs.py           # /api/logs - Log retrieval
```

---

## Backend Agent Architecture

The agent system implements a **multi-agent orchestration pattern** for AI-powered task execution.

### Agent Hierarchy

```
                        ┌─────────────────────────────┐
                        │     Agent Orchestrator      │
                        │        (run.py)             │
                        └─────────────┬───────────────┘
                                      │
              ┌───────────────────────┼───────────────────────┐
              ▼                       ▼                       ▼
    ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
    │ Spec Pipeline   │     │  Build Pipeline │     │   QA Pipeline   │
    │                 │     │                 │     │                 │
    │ ┌─────────────┐ │     │ ┌─────────────┐ │     │ ┌─────────────┐ │
    │ │Spec Gatherer│ │     │ │  Planner    │ │     │ │QA Reviewer  │ │
    │ └─────────────┘ │     │ │   Agent     │ │     │ └─────────────┘ │
    │ ┌─────────────┐ │     │ └─────────────┘ │     │ ┌─────────────┐ │
    │ │ Spec Writer │ │     │ ┌─────────────┐ │     │ │  QA Fixer   │ │
    │ └─────────────┘ │     │ │   Coder     │ │     │ └─────────────┘ │
    │ ┌─────────────┐ │     │ │   Agent     │ │     │        │        │
    │ │ Spec Critic │ │     │ └─────────────┘ │     │     (loop)      │
    │ └─────────────┘ │     │        │        │     │                 │
    └─────────────────┘     │   (iterative)   │     └─────────────────┘
                            └─────────────────┘
```

### Agent Types and Responsibilities

| Agent | File | Purpose | System Prompt |
|-------|------|---------|---------------|
| **Spec Gatherer** | `spec/phases/gatherer.py` | Collects requirements from user | `spec_gatherer.md` |
| **Spec Writer** | `spec/phases/writer.py` | Creates detailed spec.md | `spec_writer.md` |
| **Spec Critic** | `spec/phases/critic.py` | Reviews spec quality | `spec_critic.md` |
| **Planner** | `agents/planner.py` | Creates implementation_plan.json | `planner.md` |
| **Coder** | `agents/coder.py` | Implements subtasks | `coder.md` |
| **QA Reviewer** | `qa/reviewer.py` | Validates against criteria | `qa_reviewer.md` |
| **QA Fixer** | `qa/fixer.py` | Resolves QA issues | `qa_fixer.md` |

### Agent Execution Model

Each agent runs within a **Claude SDK session**:

```python
# Simplified agent execution model
from claude_agent_sdk import ClaudeSDKClient

def create_agent_session(
    agent_type: str,
    project_dir: Path,
    spec_dir: Path,
    model: str = "claude-sonnet-4-5-20250929"
) -> ClaudeSDKClient:
    """
    Creates configured Claude SDK client.

    Configuration includes:
    - Security hooks for command validation
    - Tool permissions based on agent type
    - MCP server integration
    - Extended thinking support (Planner agent)
    """

    # Load system prompt for agent type
    system_prompt = load_prompt(agent_type)

    # Configure tool permissions
    permissions = get_agent_permissions(agent_type)

    # Create client with security hooks
    client = ClaudeSDKClient(
        model=model,
        system_prompt=system_prompt,
        tool_permissions=permissions,
        security_hooks=create_security_hooks(project_dir),
        max_thinking_tokens=16384 if agent_type == "planner" else None
    )

    return client
```

### Agent Tool Permissions

Different agents have different tool access levels:

| Tool | Planner | Coder | QA Reviewer | QA Fixer |
|------|---------|-------|-------------|----------|
| Read | Yes | Yes | Yes | Yes |
| Write | No | Yes | No | Yes |
| Edit | No | Yes | No | Yes |
| Bash | Limited | Yes | Yes | Yes |
| Glob | Yes | Yes | Yes | Yes |
| Grep | Yes | Yes | Yes | Yes |
| Task | Yes | Yes | No | No |

### Memory System (Graphiti)

The agent system includes an optional knowledge graph memory:

```
┌─────────────────────────────────────────────────────────────────┐
│                   Graphiti Memory Architecture                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   Agent Session                                                  │
│        │                                                         │
│        ▼                                                         │
│   ┌────────────────┐                                            │
│   │ Memory Manager │                                            │
│   │                │                                            │
│   │ get_context()  │───► Retrieves relevant context for task    │
│   │ add_insight()  │───► Stores learnings from session          │
│   │ search()       │───► Semantic search across memories        │
│   └────────────────┘                                            │
│           │                                                      │
│           ▼                                                      │
│   ┌────────────────────────────────────────────────────────┐    │
│   │              LadybugDB (Embedded Graph DB)              │    │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐  │    │
│   │  │  Nodes   │  │  Edges   │  │  Vector Embeddings   │  │    │
│   │  │ (Facts)  │  │(Relations)│  │  (Semantic Search)  │  │    │
│   │  └──────────┘  └──────────┘  └──────────────────────┘  │    │
│   └────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Flow

### Task Execution Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      Complete Task Execution Flow                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1. TASK CREATION                                                        │
│  ─────────────────                                                       │
│                                                                          │
│  User (Browser)                                                          │
│       │                                                                  │
│       │ Click "New Task"                                                 │
│       ▼                                                                  │
│  TaskCreationWizard ──► POST /api/projects/{id}/tasks ──► Create spec   │
│       │                                                                  │
│       │ Spec Pipeline (Gatherer → Writer → Critic)                      │
│       ▼                                                                  │
│  spec.md + requirements.json created                                     │
│                                                                          │
│  2. PLANNING PHASE                                                       │
│  ─────────────────                                                       │
│                                                                          │
│  User clicks "Start"                                                     │
│       │                                                                  │
│       │ POST /api/tasks/{id}/start                                      │
│       ▼                                                                  │
│  AgentService.start_task()                                              │
│       │                                                                  │
│       │ subprocess.spawn(run.py)                                        │
│       ▼                                                                  │
│  Planner Agent ──────────────────────────────────────────────────────►  │
│       │  - Reads spec.md                                                │
│       │  - Analyzes codebase                                            │
│       │  - Creates implementation_plan.json                             │
│       ▼                                                                  │
│  WebSocket: task:status = "planning" ──► useTaskStore.updateStatus()   │
│                                                                          │
│  3. CODING PHASE                                                         │
│  ───────────────                                                         │
│                                                                          │
│  For each subtask in implementation_plan.json:                          │
│       │                                                                  │
│       │ Git worktree: .magestic-ai/worktrees/tasks/{id}/                │
│       ▼                                                                  │
│  Coder Agent ────────────────────────────────────────────────────────►  │
│       │  - Reads subtask from plan                                      │
│       │  - Implements code changes                                      │
│       │  - Commits changes                                              │
│       │  - Updates subtask status                                       │
│       ▼                                                                  │
│  WebSocket: task:progress ──► useTaskStore.setProgress()                │
│                                                                          │
│  4. QA REVIEW PHASE                                                      │
│  ──────────────────                                                      │
│                                                                          │
│  QA Reviewer Agent ──────────────────────────────────────────────────►  │
│       │  - Reviews all changes against acceptance criteria              │
│       │  - Creates qa_report.md                                         │
│       │  - If issues: creates QA_FIX_REQUEST.md                        │
│       ▼                                                                  │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                          QA Loop                                    │ │
│  │  ┌───────────────┐    Issues?    ┌──────────────┐                  │ │
│  │  │  QA Reviewer  │───── Yes ────►│  QA Fixer    │                  │ │
│  │  │               │◄──────────────│              │                  │ │
│  │  └───────────────┘               └──────────────┘                  │ │
│  │         │                                                           │ │
│  │        No Issues (max 10 iterations)                               │ │
│  │         ▼                                                           │ │
│  │    QA Approved                                                      │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  5. HUMAN REVIEW                                                         │
│  ───────────────                                                         │
│                                                                          │
│  WebSocket: task:status = "human_review"                                │
│       │                                                                  │
│       │ User reviews changes in UI                                      │
│       │ - Diff viewer                                                   │
│       │ - Terminal access                                               │
│       │ - Manual testing                                                │
│       ▼                                                                  │
│  Approve or Request Changes                                             │
│                                                                          │
│  6. MERGE                                                                │
│  ────────                                                                │
│                                                                          │
│  User clicks "Merge"                                                     │
│       │                                                                  │
│       │ POST /api/tasks/{id}/merge                                      │
│       ▼                                                                  │
│  Git merge worktree → main branch                                       │
│  Cleanup worktree                                                        │
│  Task status = "done"                                                    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Real-Time Update Flow

```
Backend Agent                 Web Server                    Frontend
─────────────                 ──────────                    ────────

Agent outputs
progress update
      │
      │ Write to progress file
      │ OR stdout parsing
      ▼
      │
      └────────────────► Event Bus
                              │
                              │ Broadcast to
                              │ connected clients
                              ▼
                         WebSocket
                         /ws/events
                              │
                              └────────────────► WebSocketManager
                                                      │
                                                      │ Parse event type
                                                      ▼
                                                 Event Router
                                                      │
                                                      ├─► task:progress
                                                      │       │
                                                      │       ▼
                                                      │   useTaskStore
                                                      │   .setProgress()
                                                      │       │
                                                      │       ▼
                                                      │   TaskCard
                                                      │   re-render
                                                      │
                                                      └─► task:status
                                                              │
                                                              ▼
                                                          KanbanBoard
                                                          move card
```

---

## Communication Protocols

### REST API

All REST endpoints follow these conventions:

| Aspect | Convention |
|--------|------------|
| **Base Path** | `/api/*` |
| **Authentication** | `Authorization: Bearer {token}` |
| **Content Type** | `application/json` |
| **Error Format** | `{ "detail": "Error message" }` |
| **Success Format** | Resource object or `{ "success": true }` |

### WebSocket Protocol

WebSocket connections require authentication:

```javascript
// Connection with token
const ws = new WebSocket(`ws://localhost:8000/ws/events?token=${token}`);

// Message format
{
  "type": "task:progress",
  "data": {
    "task_id": "001-feature",
    "phase": "coding",
    "message": "Implementing subtask 2 of 5",
    "progress": 40,
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

### Event Types

| Event | Direction | Description |
|-------|-----------|-------------|
| `task:status` | Server → Client | Task status changed |
| `task:progress` | Server → Client | Task execution progress |
| `task:log` | Server → Client | Agent log entry |
| `task:error` | Server → Client | Task error occurred |
| `task:update` | Server → Client | Task data updated |
| `roadmap:progress` | Server → Client | Roadmap generation progress |
| `ideation:progress` | Server → Client | Ideation generation progress |
| `changelog:progress` | Server → Client | Changelog generation progress |

---

## Storage Architecture

### File-Based Storage Design

MagesticAI intentionally uses **file-based storage** instead of a traditional database:

| Storage Type | Location | Purpose |
|--------------|----------|---------|
| **App Data** | `~/.magestic-ai/` | Global application data |
| **Project Data** | `{project}/.magestic-ai/` | Per-project task data |
| **Git Worktrees** | `{project}/.magestic-ai/worktrees/` | Isolated task branches |

### Global App Data (`~/.magestic-ai/`)

```
~/.magestic-ai/
├── projects.json        # List of registered projects
│                        # [{ id, path, name, createdAt }]
│
├── settings.json        # Application settings
│                        # { theme, language, defaultModel, ... }
│
├── .token               # API authentication token
│                        # Auto-generated on first run
│
├── claude-profiles.json # Claude model profiles
│                        # { profiles: [{ name, model, settings }] }
│
└── logs/                # Server logs
    ├── server.log       # General server logs
    ├── errors.log       # Error logs
    └── agent.log        # Agent execution logs
```

### Per-Project Data (`{project}/.magestic-ai/`)

```
{project}/
└── .magestic-ai/
    ├── specs/
    │   └── {task-id}/                 # e.g., 001-add-login
    │       ├── spec.md                # Feature specification
    │       ├── requirements.json      # User requirements
    │       ├── context.json           # Codebase context analysis
    │       ├── implementation_plan.json  # Subtask breakdown
    │       ├── task_logs.json         # Execution history
    │       ├── qa_report.md           # QA validation results
    │       ├── QA_FIX_REQUEST.md      # Issues to resolve
    │       ├── build-progress.txt     # Human-readable progress
    │       └── graphiti/              # Memory data (if enabled)
    │           └── ladybug.db         # Embedded graph database
    │
    └── worktrees/
        └── tasks/
            └── {task-id}/             # Git worktree (full repo clone)
                ├── ... (project files)
                └── .git               # Worktree git data
```

### Data Model

#### Project (`projects.json`)

```json
{
  "projects": [
    {
      "id": "proj-abc123",
      "path": "/home/user/my-project",
      "name": "My Project",
      "createdAt": "2024-01-15T10:00:00Z",
      "lastOpenedAt": "2024-01-15T12:00:00Z"
    }
  ]
}
```

#### Task (`implementation_plan.json`)

```json
{
  "task_id": "001-add-login",
  "title": "Add user login feature",
  "description": "Implement authentication with JWT",
  "status": "in_progress",
  "created_at": "2024-01-15T10:00:00Z",
  "phases": [
    {
      "id": "phase-1",
      "name": "Backend Implementation",
      "subtasks": [
        {
          "id": "1.1",
          "title": "Create user model",
          "status": "completed",
          "estimated_effort": "medium"
        }
      ]
    }
  ],
  "qa_signoff": {
    "status": "pending",
    "issues": null,
    "tests_passed": null
  }
}
```

---

## Security Architecture

### Authentication Model

```
┌─────────────────────────────────────────────────────────────────┐
│                    Authentication Flow                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Server Startup                                                  │
│       │                                                          │
│       │ Generate or load token                                   │
│       ▼                                                          │
│  ~/.magestic-ai/.token                                      │
│       │                                                          │
│       │ Token printed to console                                 │
│       ▼                                                          │
│  "API Token: abc123..."                                         │
│                                                                  │
│  ─────────────────────────────────────────────────────────────  │
│                                                                  │
│  Client Authentication                                           │
│       │                                                          │
│       │ Read token from localStorage                            │
│       │ (or input from user)                                    │
│       ▼                                                          │
│  Every Request:                                                  │
│  Authorization: Bearer {token}                                   │
│       │                                                          │
│       │ TokenAuthMiddleware                                      │
│       ▼                                                          │
│  Validate token matches stored token                            │
│       │                                                          │
│       ├─► Match: Proceed to route handler                       │
│       └─► No Match: 401 Unauthorized                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Command Validation (Three-Layer Security)

```
┌─────────────────────────────────────────────────────────────────┐
│                 Command Security Layers                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Layer 1: OS Sandbox                                            │
│  ────────────────────                                           │
│  - Bash commands run in isolated environment                    │
│  - Process isolation via subprocess                             │
│                                                                  │
│  Layer 2: Filesystem Restrictions                               │
│  ────────────────────────────────                               │
│  - Agents restricted to project directory                       │
│  - No access to system files                                    │
│  - Worktree isolation per task                                  │
│                                                                  │
│  Layer 3: Command Allowlist                                     │
│  ──────────────────────────                                     │
│  - Base commands always allowed:                                │
│    ls, cd, mkdir, cat, echo, git, pwd, rm, mv, cp              │
│                                                                  │
│  - Stack-specific commands (auto-detected):                     │
│    Node.js: npm, npx, yarn, pnpm, node                         │
│    Python: pip, python, pytest, uv                             │
│    Rust: cargo, rustc                                          │
│    Go: go                                                      │
│    Docker: docker, docker-compose                              │
│                                                                  │
│  Security Profile (.magestic-ai-security.json):                 │
│  {                                                              │
│    "allowed_commands": ["npm", "git", "python", ...],          │
│    "capabilities": {                                            │
│      "is_node": true,                                          │
│      "is_python": true                                         │
│    },                                                           │
│    "custom_commands": []                                        │
│  }                                                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Design Decisions

### 1. Three-Tier Architecture

**Decision:** Separate frontend, web server, and agent system into distinct applications.

**Rationale:**
- **Scalability** - Components can be scaled independently
- **Maintainability** - Clear separation of concerns
- **Technology Choice** - Best tool for each job (React, FastAPI, Claude SDK)
- **Deployment Flexibility** - Can run on different machines

### 2. File-Based Storage

**Decision:** Use JSON files instead of a traditional database.

**Rationale:**
- **Simplicity** - No database setup required
- **Portability** - Project data travels with the repository
- **Git Integration** - Task specs can be version controlled
- **Debugging** - Human-readable data files

**Trade-offs:**
- Not suitable for concurrent writes (single-user by design)
- No complex queries (acceptable for project-level data)

### 3. Git Worktree Isolation

**Decision:** Each task executes in its own git worktree.

**Rationale:**
- **Isolation** - Tasks don't interfere with each other
- **Safety** - Main branch remains untouched until merge
- **Parallelism** - Multiple tasks can run simultaneously
- **Rollback** - Easy to discard failed task changes

### 4. WebSocket for Real-Time Updates

**Decision:** Use WebSocket for all real-time communication.

**Rationale:**
- **Efficiency** - Persistent connection, no polling overhead
- **Bidirectional** - Support for terminal I/O
- **Real-time** - Instant progress updates

### 5. Agent Subprocess Model

**Decision:** Run agents as separate Python subprocesses.

**Rationale:**
- **Stability** - Agent crash doesn't affect web server
- **Resource Isolation** - Memory/CPU limits per agent
- **Logging** - Clear separation of agent logs
- **Termination** - Easy to kill runaway agents

### 6. Adapter Pattern for API

**Decision:** Use `window.API` interface for all API calls.

**Rationale:**
- **Abstraction** - UI code doesn't know transport details
- **Testability** - Easy to mock for testing
- **Migration** - Could switch backends without UI changes
- **Consistency** - Single interface for all API operations

---

## Scalability Considerations

### Current Limitations

| Aspect | Limitation | Reason |
|--------|------------|--------|
| **Concurrent Tasks** | 5 (default) | Resource management |
| **Terminals** | 20 (default) | Memory per PTY |
| **File Size** | 10MB | In-memory processing |
| **Projects** | Unlimited | File-based storage |

### Horizontal Scaling

The architecture supports horizontal scaling through:

1. **Multiple Web Servers** - Behind load balancer (requires sticky sessions for WebSocket)
2. **Distributed Agents** - Agent workers on multiple machines
3. **Shared Storage** - NFS or cloud storage for `~/.magestic-ai/`

### Performance Optimizations

| Area | Optimization |
|------|-------------|
| **Frontend** | React 19 concurrent features, virtual scrolling |
| **API** | Async FastAPI, connection pooling |
| **WebSocket** | Binary protocol option for terminals |
| **Agents** | Memory caching with Graphiti |

---

## Further Reading

- **[Development Setup](DEVELOPMENT-SETUP.md)** - Set up your development environment
- **[API Reference](API-REFERENCE.md)** - Complete API documentation
- **[Task Workflow](TASK-WORKFLOW.md)** - Detailed task lifecycle
- **[Technical Docs](../DOCS.md)** - In-depth technical reference

---

**MagesticAI** - Understanding the architecture enables better contributions.
