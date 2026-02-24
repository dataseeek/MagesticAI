# Claude Code Manager Web - Technical Documentation

Comprehensive technical documentation for contributors and developers.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Tech Stack](#3-tech-stack)
4. [Installation](#4-installation)
5. [Configuration](#5-configuration)
6. [Backend Web Server](#6-backend-web-server)
7. [Frontend Web](#7-frontend-web)
8. [Backend Agents](#8-backend-agents)
9. [Database & Storage](#9-database--storage)
10. [API Reference](#10-api-reference)
11. [WebSocket Events](#11-websocket-events)
12. [State Management](#12-state-management)
13. [Internationalization](#13-internationalization)
14. [Security](#14-security)
15. [Testing](#15-testing)
16. [Deployment](#16-deployment)
17. [Troubleshooting](#17-troubleshooting)

---

## 1. Overview

### Purpose

Claude Code Manager Web is a web-based platform for managing AI-powered coding tasks through coordinated autonomous agents. It enables:

- **Task Automation** - Create specs, plan implementations, and execute code automatically
- **Multi-Agent Orchestration** - Planner, Coder, and QA agents work together
- **Browser Access** - Full functionality from any modern browser
- **Real-time Monitoring** - Watch task progress and logs in real-time

### System Requirements

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| Node.js | 24.0.0 | 24+ LTS |
| Python | 3.12 | 3.12+ |
| npm | 10.0.0 | 10+ |
| RAM | 4 GB | 8 GB+ |
| Disk | 2 GB | 10 GB+ |
| OS | Linux, macOS, Windows | Linux, macOS |

### Key Features

| Feature | Description |
|---------|-------------|
| Kanban Board | Visual task management with drag-and-drop |
| Multi-Terminal | PTY terminals in browser via xterm.js |
| Code Editor | Monaco editor with syntax highlighting |
| Git Worktrees | Isolated builds per task |
| AI QA | Automated code review and validation |
| Memory System | Cross-session learning via Graphiti |
| i18n | English, French, Portuguese (Brazil) |

---

## 2. Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Browser Client                            │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  React 19 + Vite + TypeScript                           │    │
│  │  ├── Components (70+)                                    │    │
│  │  ├── Zustand Stores (16)                                 │    │
│  │  ├── WebSocket Manager                                   │    │
│  │  └── REST API Client                                     │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              │                                   │
│              ┌───────────────┴───────────────┐                  │
│              │ HTTP/REST     │ WebSocket     │                  │
│              │ :5173→:8000   │ :5173→:8000   │                  │
│              └───────────────┬───────────────┘                  │
└──────────────────────────────┼──────────────────────────────────┘
                               │
┌──────────────────────────────┼──────────────────────────────────┐
│                        Web Server                                │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  FastAPI + Uvicorn (Port 8000)                          │    │
│  │  ├── Routes (/api/*)                                     │    │
│  │  ├── WebSockets (/ws/*)                                  │    │
│  │  ├── PTY Manager                                         │    │
│  │  └── Agent Service                                       │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              │                                   │
│              ┌───────────────┴───────────────┐                  │
│              │ Subprocess    │ File I/O      │                  │
│              └───────────────┬───────────────┘                  │
└──────────────────────────────┼──────────────────────────────────┘
                               │
┌──────────────────────────────┼──────────────────────────────────┐
│                      Backend Agents                              │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Claude Agent SDK                                        │    │
│  │  ├── Planner Agent                                       │    │
│  │  ├── Coder Agent                                         │    │
│  │  ├── QA Reviewer                                         │    │
│  │  ├── QA Fixer                                            │    │
│  │  └── Graphiti Memory (LadybugDB)                         │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
User Action → React Component → Zustand Store → API Client
                                                    │
                                              REST/WebSocket
                                                    │
                                              FastAPI Route
                                                    │
                                              Agent Service
                                                    │
                                           Claude Agent SDK
                                                    │
                                             Git Worktree
```

### Directory Structure

```
Claude-Code-Manager-Web/
├── apps/
│   ├── frontend-web/           # React web frontend
│   │   ├── src/
│   │   │   ├── App.tsx         # Main app component
│   │   │   ├── main.tsx        # Entry point
│   │   │   ├── components/     # React components
│   │   │   ├── stores/         # Zustand state stores
│   │   │   ├── hooks/          # Custom React hooks
│   │   │   ├── pages/          # Page components
│   │   │   ├── lib/            # Utilities
│   │   │   ├── contexts/       # React contexts
│   │   │   └── shared/         # Types, i18n, constants
│   │   ├── vite.config.ts
│   │   └── package.json
│   │
│   ├── web-server/             # FastAPI backend
│   │   └── server/
│   │       ├── main.py         # FastAPI app entry
│   │       ├── config.py       # Configuration
│   │       ├── auth.py         # Authentication
│   │       ├── routes/         # REST API routes
│   │       ├── websockets/     # WebSocket handlers
│   │       ├── services/       # Business logic
│   │       └── pty/            # Terminal management
│   │
│   ├── backend/                # Python agent system
│   │   ├── run.py              # CLI entry point
│   │   ├── spec_runner.py      # Spec creation
│   │   ├── core/               # Client, auth, security
│   │   ├── agents/             # Agent implementations
│   │   ├── qa/                 # QA agents
│   │   ├── spec/               # Spec pipeline
│   │   ├── security/           # Command validation
│   │   ├── integrations/       # Graphiti, Linear, GitHub
│   │   └── prompts/            # Agent system prompts
│   │
├── tests/                      # Test suite
├── scripts/                    # Build scripts
├── guides/                     # Additional docs
└── package.json                # Root package
```

---

## 3. Tech Stack

### Frontend Technologies

| Package | Version | Purpose |
|---------|---------|---------|
| `react` | 19.2.3 | UI framework |
| `react-dom` | 19.2.3 | DOM rendering |
| `typescript` | 5.9.3 | Type safety |
| `vite` | 7.2.7 | Build tool |
| `tailwindcss` | 4.1.17 | CSS framework |
| `zustand` | 5.0.9 | State management |
| `@radix-ui/*` | Latest | Accessible UI primitives |
| `@xterm/xterm` | 6.0.0 | Terminal emulator |
| `@xterm/addon-fit` | 0.10.0 | Terminal sizing |
| `@xterm/addon-webgl` | 0.18.0 | GPU rendering |
| `@monaco-editor/react` | 4.6.0 | Code editor |
| `i18next` | 25.7.3 | Internationalization |
| `react-i18next` | 16.5.0 | React i18n bindings |
| `@dnd-kit/core` | 6.3.1 | Drag and drop |
| `@dnd-kit/sortable` | 10.0.0 | Sortable lists |
| `react-markdown` | 10.1.0 | Markdown rendering |
| `@tanstack/react-virtual` | 3.13.13 | Virtual scrolling |
| `lucide-react` | 0.562.0 | Icons |
| `motion` | 12.23.26 | Animations |
| `zod` | 4.2.1 | Schema validation |

### Backend Web Server Technologies

| Package | Version | Purpose |
|---------|---------|---------|
| `fastapi` | Latest | REST framework |
| `uvicorn` | Latest | ASGI server |
| `pydantic` | v2 | Data validation |
| `websockets` | Latest | WebSocket support |
| `ptyprocess` | Latest | PTY handling |
| `gitpython` | Latest | Git operations |
| `aiofiles` | Latest | Async file I/O |
| `python-dotenv` | Latest | Environment vars |

### Backend Agent Technologies

| Package | Version | Purpose |
|---------|---------|---------|
| `claude-agent-sdk` | Latest | Claude AI SDK |
| `graphiti-core` | Latest | Knowledge graph |
| `ladybugdb` | Embedded | Graph database |
| `anthropic` | Latest | Anthropic API |
| `openai` | Latest | OpenAI embeddings |
| `voyageai` | Latest | Voyage embeddings |

---

## 4. Installation

### Prerequisites

```bash
# Check versions
node --version    # Must be >= 24.0.0
npm --version     # Must be >= 10.0.0
python3 --version # Must be >= 3.12

# Install Claude Code CLI and get token
npm install -g @anthropic-ai/claude-code
claude setup-token
```

### Step-by-Step Installation

```bash
# 1. Clone repository
git clone https://github.com/dataseeek/Claude-Code-Manager-Web.git
cd Claude-Code-Manager-Web

# 2. Install all dependencies
npm run install:all

# 3. Create environment files
cp apps/backend/.env.example apps/backend/.env
cp apps/web-server/.env.example apps/web-server/.env

# 4. Edit .env files with your tokens
# apps/backend/.env:
#   CLAUDE_CODE_OAUTH_TOKEN=your-token
#   GRAPHITI_ENABLED=true
#
# apps/web-server/.env:
#   AUTO_CLAUDE_HOST=0.0.0.0
#   AUTO_CLAUDE_PORT=8000
```

### Running the Application

**Terminal 1 - Backend Server:**
```bash
cd apps/web-server
source .venv/bin/activate  # Linux/macOS
# OR: .venv\Scripts\activate  # Windows
python -m server.main
```

**Terminal 2 - Frontend:**
```bash
cd apps/frontend-web
npm run dev
```

**Access:** http://localhost:5173

---

## 5. Configuration

### Environment Variables Reference

#### Backend (`apps/backend/.env`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CLAUDE_CODE_OAUTH_TOKEN` | Yes | - | Claude Code OAuth token |
| `GRAPHITI_ENABLED` | No | `false` | Enable Graphiti memory |
| `LINEAR_API_KEY` | No | - | Linear integration |
| `GITHUB_TOKEN` | No | - | GitHub integration |
| `ANTHROPIC_API_KEY` | No | - | Alternative to OAuth |

#### Web Server (`apps/web-server/.env`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AUTO_CLAUDE_HOST` | No | `0.0.0.0` | Server bind address |
| `AUTO_CLAUDE_PORT` | No | `8000` | Server port |
| `AUTO_CLAUDE_DEBUG` | No | `false` | Enable debug mode |
| `AUTO_CLAUDE_API_TOKEN` | No | Auto-generated | Fixed API token |
| `AUTO_CLAUDE_SSL_ENABLED` | No | `false` | Enable HTTPS |

#### Frontend (`apps/frontend-web/.env`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VITE_API_BASE_URL` | No | `/api` | API base path |
| `VITE_WS_BASE_URL` | No | `ws://localhost:8000` | WebSocket URL |
| `VITE_API_URL` | No | `http://localhost:8000` | Backend URL |

### Configuration Files

| File | Location | Purpose |
|------|----------|---------|
| `settings.json` | `~/.auto-claude-web/` | App settings |
| `projects.json` | `~/.auto-claude-web/` | Project list |
| `.token` | `~/.auto-claude-web/` | API auth token |
| `claude-profiles.json` | `~/.auto-claude-web/` | Claude profiles |

---

## 6. Backend Web Server

### Directory Structure (`apps/web-server/`)

```
server/
├── main.py               # FastAPI application
├── config.py             # Pydantic settings
├── auth.py               # Token authentication
├── logging_config.py     # Logging setup
├── routes/
│   ├── projects.py       # /api/projects
│   ├── tasks.py          # /api/tasks (CRUD)
│   ├── execution.py      # /api/tasks (execution)
│   ├── files.py          # /api/files
│   ├── terminal.py       # /api/terminals
│   ├── settings.py       # /api/settings
│   ├── git.py            # /api/git, /api/claude-code
│   ├── github.py         # /api/github
│   ├── gitlab.py         # /api/gitlab
│   ├── context.py        # /api/memory
│   ├── roadmap.py        # /api/projects/{id}/roadmap
│   ├── changelog.py      # /api/projects/{id}/changelog
│   └── logs.py           # /api/logs
├── websockets/
│   ├── events.py         # /ws/events
│   ├── terminal.py       # /ws/terminal/{id}
│   ├── progress.py       # /ws/tasks/{id}/progress
│   └── logs.py           # /ws/tasks/{id}/logs
├── services/
│   ├── agent_service.py  # Agent execution
│   └── insights_service.py
└── pty/
    ├── manager.py        # PTY session management
    └── session.py        # Individual PTY sessions
```

### Key Classes

#### `AgentService` (`services/agent_service.py`)

Orchestrates task execution:

```python
class AgentService:
    async def start_task(task_id: str, options: StartTaskRequest) -> None:
        """Start task execution in background."""

    async def get_task_status(task_id: str) -> TaskExecutionStatus:
        """Get current execution status."""

    def register_progress_callback(task_id: str, callback: Callable):
        """Register for progress updates."""
```

#### `PTYManager` (`pty/manager.py`)

Manages terminal sessions:

```python
class PTYManager:
    def create_session(cwd: str, env: dict) -> str:
        """Create new PTY session, returns session ID."""

    def get_session(session_id: str) -> PTYSession:
        """Get session by ID."""

    def close_session(session_id: str) -> None:
        """Close and cleanup session."""
```

### Authentication Flow

```
1. Server starts → generates token → saves to ~/.auto-claude-web/.token
2. Client reads token from localStorage
3. All /api/* requests include: Authorization: Bearer {token}
4. WebSocket connects with: ?token={token} or Bearer header
5. TokenAuthMiddleware validates on each request
```

---

## 7. Frontend Web

### Directory Structure (`apps/frontend-web/`)

```
src/
├── App.tsx                  # Main router & auth flow
├── main.tsx                 # React entry point
├── index.css                # Tailwind imports
├── components/
│   ├── Sidebar.tsx          # Navigation sidebar
│   ├── ProjectTabBar.tsx    # Project tabs
│   ├── KanbanBoard.tsx      # Task kanban view
│   ├── TerminalGrid.tsx     # Multi-terminal layout
│   ├── Terminal.tsx         # Single terminal
│   ├── Roadmap.tsx          # Feature roadmap
│   ├── Ideation.tsx         # AI ideation
│   ├── Context.tsx          # Project context
│   ├── Worktrees.tsx        # Git worktrees
│   ├── GitHubIssues.tsx     # GitHub integration
│   ├── GitLabIssues.tsx     # GitLab integration
│   ├── TaskCreationWizard.tsx
│   ├── TaskDetailModal.tsx
│   ├── AppSettings.tsx
│   ├── ui/                  # Shadcn/Radix components
│   ├── task-detail/         # Task detail components
│   ├── terminal/            # Terminal components
│   ├── settings/            # Settings components
│   ├── ideation/            # Ideation components
│   ├── roadmap/             # Roadmap components
│   └── changelog/           # Changelog components
├── stores/
│   ├── project-store.ts     # Projects & tabs
│   ├── task-store.ts        # Tasks & execution
│   ├── settings-store.ts    # User settings
│   ├── terminal-store.ts    # Terminals
│   ├── roadmap-store.ts     # Roadmap data
│   ├── ideation-store.ts    # Ideation data
│   ├── auth-store.ts        # Authentication
│   ├── context-store.ts     # Project context
│   ├── insights-store.ts    # Insights
│   ├── changelog-store.ts   # Changelog
│   ├── github/              # GitHub stores
│   └── gitlab/              # GitLab stores
├── hooks/
│   ├── useIpc.ts            # IPC event handling
│   ├── useVirtualizedTree.ts
│   └── use-toast.ts
├── lib/
│   ├── api-adapter.ts       # API adapter
│   ├── api-client.ts        # HTTP client
│   ├── websocket.ts         # WebSocket manager
│   ├── auth.ts              # Auth utilities
│   └── logger.ts            # Client logging
├── pages/
│   ├── LoginPage.tsx
│   └── EditorPage.tsx
├── contexts/
│   └── ViewStateContext.tsx
└── shared/
    ├── types/               # TypeScript types
    ├── constants/           # App constants
    ├── utils/               # Utilities
    └── i18n/                # Translations
        └── locales/
            ├── en/          # English
            ├── fr/          # French
            └── pt-BR/       # Portuguese
```

### Key Components

#### `App.tsx`

Main application with routing:

```tsx
function App() {
  // Auth check
  if (!isAuthenticated) return <LoginPage />;

  // Main layout
  return (
    <div className="flex h-screen">
      <Sidebar />
      <main className="flex-1">
        <ProjectTabBar />
        {/* View router based on currentView */}
        {currentView === 'kanban' && <KanbanBoard />}
        {currentView === 'terminals' && <TerminalGrid />}
        {/* ... other views */}
      </main>
    </div>
  );
}
```

#### `KanbanBoard.tsx`

Task board with drag-and-drop:

```tsx
function KanbanBoard() {
  const { tasks } = useTaskStore();

  return (
    <DndContext onDragEnd={handleDragEnd}>
      <div className="flex gap-4">
        <Column status="backlog" tasks={filterByStatus('backlog')} />
        <Column status="in_progress" tasks={filterByStatus('in_progress')} />
        <Column status="ai_review" tasks={filterByStatus('ai_review')} />
        <Column status="human_review" tasks={filterByStatus('human_review')} />
        <Column status="done" tasks={filterByStatus('done')} />
      </div>
    </DndContext>
  );
}
```

### API Adapter Pattern

The `api-adapter.ts` provides a unified interface for API access:

```typescript
// Web API interface
window.API = {
  getProjects: () => api.get('/api/projects'),
  createProject: (data) => api.post('/api/projects', data),
  startTask: (id, options) => api.post(`/api/tasks/${id}/start`, options),
  // ... 50+ methods
};
```

---

## 8. Backend Agents

### Directory Structure (`apps/backend/`)

```
├── run.py                    # Main CLI entry
├── spec_runner.py            # Spec creation CLI
├── core/
│   ├── client.py             # Claude SDK client factory
│   ├── auth.py               # OAuth token management
│   └── workspace/            # Worktree management
├── agents/
│   ├── planner.py            # Creates implementation plans
│   ├── coder.py              # Implements subtasks
│   ├── session.py            # Agent session execution
│   ├── memory_manager.py     # Memory orchestration
│   ├── utils.py              # Shared utilities
│   └── tools_pkg/
│       ├── models.py         # Tool definitions
│       └── permissions.py    # Agent tool permissions
├── qa/
│   ├── reviewer.py           # QA validation
│   ├── fixer.py              # Issue resolution
│   └── loop.py               # QA iteration loop
├── spec/
│   ├── pipeline/
│   │   └── orchestrator.py   # Spec creation pipeline
│   └── phases/
│       └── executor.py       # Phase execution
├── security/
│   ├── main.py               # Command validation
│   ├── hooks.py              # MCP security hooks
│   └── validators/           # Specific validators
├── integrations/
│   └── graphiti/             # Knowledge graph memory
│       ├── queries_pkg/
│       │   ├── graphiti.py   # Main memory class
│       │   ├── client.py     # LadybugDB client
│       │   ├── queries.py    # Graph operations
│       │   ├── search.py     # Semantic search
│       │   └── schema.py     # Graph schema
│       └── insight_extractor.py
└── prompts/                   # Agent system prompts
    ├── planner.md
    ├── coder.md
    ├── qa_reviewer.md
    ├── qa_fixer.md
    ├── spec_gatherer.md
    ├── spec_writer.md
    └── complexity_assessor.md
```

### Agent Types

| Agent | Purpose | Prompts |
|-------|---------|---------|
| **Planner** | Creates implementation plan with subtasks | `planner.md` |
| **Coder** | Implements subtasks iteratively | `coder.md`, `coder_recovery.md` |
| **QA Reviewer** | Validates against acceptance criteria | `qa_reviewer.md` |
| **QA Fixer** | Fixes issues from QA | `qa_fixer.md` |
| **Spec Gatherer** | Collects requirements | `spec_gatherer.md` |
| **Spec Writer** | Creates spec.md | `spec_writer.md` |
| **Spec Critic** | Reviews spec quality | `spec_critic.md` |

### Client Factory (`core/client.py`)

```python
def create_client(
    project_dir: Path,
    spec_dir: Path,
    model: str = "claude-sonnet-4-5-20250929",
    agent_type: str = "coder",
    max_thinking_tokens: int | None = None
) -> ClaudeSDKClient:
    """
    Creates a configured Claude SDK client with:
    - Security hooks (command validation)
    - Tool permissions based on agent_type
    - MCP server integration
    - Extended thinking support
    """
```

### Execution Flow

```
1. SPEC CREATION (spec_runner.py)
   ├── Discovery phase → gather requirements
   ├── Context phase → analyze codebase
   ├── Spec writing phase → create spec.md
   └── Validation phase → verify completeness

2. IMPLEMENTATION (run.py)
   ├── Planning phase → Planner creates subtasks
   ├── Coding phase → Coder implements subtasks
   │   ├── Load subtask
   │   ├── Run agent session
   │   ├── Post-session processing
   │   └── Update status
   └── QA phase → Review and fix loop

3. QA LOOP (qa/loop.py)
   ├── QA Reviewer validates
   ├── If issues → QA Fixer resolves
   ├── Loop until approved (max 10 iterations)
   └── Mark complete or escalate
```

---

## 9. Database & Storage

### File-Based Storage

Claude Code Manager Web uses file-based storage (no SQL database):

| Location | Content |
|----------|---------|
| `~/.auto-claude-web/` | Web interface data |
| `~/.auto-claude-web/projects.json` | Project list |
| `~/.auto-claude-web/settings.json` | App settings |
| `~/.auto-claude-web/.token` | API auth token |
| `~/.auto-claude-web/logs/` | Server logs |
| `.auto-claude/specs/` | Per-project spec data |
| `.auto-claude/worktrees/` | Git worktrees |

### Project Data Structure

```
project-root/
└── .auto-claude/
    ├── specs/
    │   └── 001-feature-name/
    │       ├── spec.md               # Feature specification
    │       ├── requirements.json     # User requirements
    │       ├── context.json          # Codebase context
    │       ├── implementation_plan.json  # Subtask plan
    │       ├── task_logs.json        # Execution logs
    │       ├── qa_report.md          # QA results
    │       ├── QA_FIX_REQUEST.md     # Issues to fix
    │       └── graphiti/             # Memory data
    └── worktrees/
        └── tasks/
            └── 001-feature-name/     # Isolated worktree
```

### Graphiti Memory System

Knowledge graph with semantic search:

```python
from integrations.graphiti.memory import get_graphiti_memory

# Get memory instance
memory = get_graphiti_memory(spec_dir, project_dir)

# Retrieve context for task
context = memory.get_context_for_session("Implementing feature X")

# Add insight from session
memory.add_session_insight("Pattern: use React hooks for state")

# Search memory
results = memory.search("authentication patterns")
```

---

## 10. API Reference

### Projects

```http
GET /api/projects
# Returns: { projects: Project[] }

POST /api/projects
# Body: { path: string, name?: string }
# Returns: Project

GET /api/projects/{id}
# Returns: Project

PUT /api/projects/{id}
# Body: Partial<Project>
# Returns: Project

DELETE /api/projects/{id}
# Returns: { success: boolean }
```

### Tasks

```http
GET /api/projects/{id}/tasks
# Returns: { tasks: Task[] }

POST /api/projects/{id}/tasks
# Body: { description: string, title?: string, ... }
# Returns: Task

GET /api/tasks/{id}
# Returns: Task

PUT /api/tasks/{id}
# Body: Partial<Task>
# Returns: Task

POST /api/tasks/{id}/start
# Body: { model?: string, profile?: string }
# Returns: { success: boolean }

GET /api/tasks/{id}/status
# Returns: TaskExecutionStatus

POST /api/tasks/{id}/stop
# Returns: { success: boolean }
```

### Files

```http
GET /api/files/list?path=/absolute/path
# Returns: { path, entries: FileEntry[], parent }

GET /api/files/read?path=/absolute/path
# Returns: { path, content, size, modified, language }

GET /api/files/search?query=text&path=/search/root
# Returns: { results: SearchResult[] }
```

### Terminals

```http
GET /api/terminals
# Returns: { terminals: TerminalInfo[] }

POST /api/terminals
# Body: { cwd?: string, name?: string }
# Returns: TerminalInfo

DELETE /api/terminals/{id}
# Returns: { success: boolean }

POST /api/terminals/{id}/resize
# Body: { cols: number, rows: number }
# Returns: { success: boolean }
```

### Settings

```http
GET /api/settings
# Returns: AppSettings

PUT /api/settings
# Body: Partial<AppSettings>
# Returns: AppSettings
```

---

## 11. WebSocket Events

### Event Types

```typescript
type EventType =
  | 'task:progress'    // Task execution progress
  | 'task:status'      // Task status change
  | 'task:error'       // Task error
  | 'task:log'         // Task log entry
  | 'task:update'      // Task data update
  | 'roadmap:progress' // Roadmap generation
  | 'ideation:progress' // Ideation generation
  | 'changelog:progress' // Changelog generation
  | 'insights:progress'; // Insights generation
```

### WebSocket Endpoints

#### `/ws/events` - Global Events

```typescript
// Connect
const ws = new WebSocket('ws://localhost:8000/ws/events?token=xxx');

// Receive events
ws.onmessage = (event) => {
  const { type, data } = JSON.parse(event.data);
  // Handle event
};
```

#### `/ws/terminal/{id}` - Terminal I/O

```typescript
// Connect
const ws = new WebSocket(`ws://localhost:8000/ws/terminal/${terminalId}?token=xxx`);

// Send input
ws.send('ls -la\r');

// Receive output
ws.onmessage = (event) => {
  terminal.write(event.data);
};

// Send control messages
ws.send(JSON.stringify({ type: 'resize', cols: 120, rows: 40 }));
```

#### `/ws/tasks/{id}/progress` - Task Progress

```typescript
interface ProgressMessage {
  phase: 'discovery' | 'planning' | 'coding' | 'qa_review' | 'qa_fixing';
  message: string;
  timestamp: string;
  subtask?: {
    id: string;
    name: string;
    progress: number;
  };
}
```

---

## 12. State Management

### Zustand Store Pattern

```typescript
// Store definition
interface TaskStore {
  tasks: Task[];
  selectedTaskId: string | null;

  // Actions
  setTasks: (tasks: Task[]) => void;
  addTask: (task: Task) => void;
  updateTask: (id: string, updates: Partial<Task>) => void;
  selectTask: (id: string | null) => void;
}

const useTaskStore = create<TaskStore>((set) => ({
  tasks: [],
  selectedTaskId: null,

  setTasks: (tasks) => set({ tasks }),
  addTask: (task) => set((state) => ({
    tasks: [...state.tasks, task]
  })),
  updateTask: (id, updates) => set((state) => ({
    tasks: state.tasks.map(t =>
      t.id === id ? { ...t, ...updates } : t
    )
  })),
  selectTask: (id) => set({ selectedTaskId: id }),
}));
```

### Available Stores

| Store | File | Purpose |
|-------|------|---------|
| `useProjectStore` | `project-store.ts` | Projects, tabs |
| `useTaskStore` | `task-store.ts` | Tasks, execution |
| `useSettingsStore` | `settings-store.ts` | User settings |
| `useTerminalStore` | `terminal-store.ts` | Terminals |
| `useRoadmapStore` | `roadmap-store.ts` | Roadmap data |
| `useIdeationStore` | `ideation-store.ts` | Ideation |
| `useAuthStore` | `auth-store.ts` | Authentication |
| `useContextStore` | `context-store.ts` | Project context |
| `useInsightsStore` | `insights-store.ts` | Insights |
| `useChangelogStore` | `changelog-store.ts` | Changelog |

---

## 13. Internationalization

### Supported Languages

| Language | Code | Completion |
|----------|------|------------|
| English | `en` | 100% |
| French | `fr` | 100% |
| Portuguese (Brazil) | `pt-BR` | 100% |

### Translation Files

```
src/shared/i18n/locales/
├── en/
│   ├── common.json       # Buttons, labels, errors
│   ├── navigation.json   # Sidebar items
│   ├── settings.json     # Settings page
│   ├── tasks.json        # Task terminology
│   ├── welcome.json      # Welcome screen
│   ├── onboarding.json   # Onboarding wizard
│   ├── dialogs.json      # Dialog content
│   ├── gitlab.json       # GitLab terms
│   ├── taskReview.json   # QA review
│   └── terminal.json     # Terminal labels
├── fr/
│   └── ... (same structure)
└── pt-BR/
    └── ... (same structure)
```

### Usage

```tsx
import { useTranslation } from 'react-i18next';

function MyComponent() {
  const { t } = useTranslation(['common', 'navigation']);

  return (
    <div>
      <h1>{t('navigation:items.kanban')}</h1>
      <button>{t('common:buttons.save')}</button>
    </div>
  );
}
```

### Adding Translations

1. Add keys to all locale files (`en/`, `fr/`, `pt-BR/`)
2. Use namespace:key format
3. Interpolation: `"Hello {{name}}"` → `t('greeting', { name: 'World' })`

---

## 14. Security

### Authentication

- **Token-based auth** stored in `~/.auto-claude-web/.token`
- Auto-generated on first server start
- Required for all `/api/*` routes
- WebSocket auth via query param or header

### Command Validation

Three-layer security model:

1. **OS Sandbox** - Bash command isolation
2. **Filesystem Permissions** - Restricted to project directory
3. **Command Allowlist** - Dynamic based on project stack

```python
# Base allowed commands
BASE_COMMANDS = ['ls', 'cd', 'mkdir', 'cat', 'echo', 'git', ...]

# Stack-specific (auto-detected)
STACK_COMMANDS = {
    'node': ['npm', 'npx', 'yarn', 'pnpm'],
    'python': ['pip', 'python', 'pytest'],
    # ...
}
```

### Security Profile

Cached in `.auto-claude-security.json`:

```json
{
  "allowed_commands": ["npm", "git", "python", ...],
  "capabilities": {
    "is_node": true,
    "is_python": true,
    "is_typescript": true
  },
  "custom_commands": []
}
```

---

## 15. Testing

### Backend Tests

```bash
# Install test dependencies
cd apps/backend
uv pip install -r ../../tests/requirements-test.txt

# Run all tests
.venv/bin/pytest tests/ -v

# Run specific test file
.venv/bin/pytest tests/test_security.py -v

# Run with coverage
.venv/bin/pytest tests/ --cov=apps/backend
```

### Frontend Tests

```bash
cd apps/frontend-web

# Run unit tests
npm test

# Watch mode
npm run test:watch

# With coverage
npm run test:coverage
```

### Test Structure

```
tests/
├── test_security.py      # Security validation tests
├── test_worktree.py      # Git worktree tests
├── test_spec.py          # Spec creation tests
├── test_agents.py        # Agent execution tests
└── conftest.py           # Pytest fixtures
```

---

## 16. Deployment

### Development

```bash
# Terminal 1: Backend
cd apps/web-server && source .venv/bin/activate && python -m server.main

# Terminal 2: Frontend
cd apps/frontend-web && npm run dev
```

### Production Build

```bash
# Build frontend
cd apps/frontend-web
npm run build
# Output: ../web-server/static/

# Start production server
cd apps/web-server
source .venv/bin/activate
AUTO_CLAUDE_DEBUG=false python -m server.main
```

### Remote Access

1. Ensure ports 8000 accessible
2. Set `AUTO_CLAUDE_HOST=0.0.0.0`
3. Configure `VITE_WS_BASE_URL` for remote WebSocket
4. Access via `http://YOUR_SERVER_IP:8000`

### HTTPS (Optional)

```bash
# Enable SSL
AUTO_CLAUDE_SSL_ENABLED=true
# Certificates auto-generated in ~/.auto-claude-web/ssl/
```

---

## 17. Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Cannot connect to backend | Verify web-server on port 8000 |
| Invalid token | Get from `~/.auto-claude-web/.token` |
| WebSocket fails | Check token, verify ports |
| Task stuck | Check logs: Settings → Logs |
| Memory errors | Set `GRAPHITI_ENABLED=true` |
| Terminal not responding | Restart terminal, check PTY |
| UI frozen | Hard refresh (Ctrl+Shift+R) |

### Log Locations

| Log | Location |
|-----|----------|
| Server logs | `~/.auto-claude-web/logs/server.log` |
| Error logs | `~/.auto-claude-web/logs/errors.log` |
| Agent logs | `~/.auto-claude-web/logs/agent.log` |
| Task logs | `.auto-claude/specs/{id}/task_logs.json` |

### Debug Mode

Enable debug logging:

```bash
# Backend
AUTO_CLAUDE_DEBUG=true python -m server.main

# Check Swagger docs
http://localhost:8000/docs
```

### Getting Help

- **Issues:** https://github.com/dataseeek/Claude-Code-Manager-Web/issues
- **Discussions:** https://github.com/dataseeek/Claude-Code-Manager-Web/discussions

---

**Documentation by DataSeek Team**
