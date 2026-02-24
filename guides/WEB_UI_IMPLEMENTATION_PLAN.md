# Auto-Claude Web UI Implementation Plan

## Overview

Convert Auto-Claude from Electron desktop app to full web UI with feature parity, Monaco editor integration, and remote access capability.

**User Requirements:**
- Full Web Replacement (no Electron)
- Simple API Token authentication
- Full IDE-like Editor (Monaco)
- Feature Parity with current Electron app

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Web Browser                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  React SPA (apps/frontend-web)                      │    │
│  │  - Kanban, Terminals, Editor, Settings, etc.        │    │
│  │  - Monaco Editor for IDE features                   │    │
│  │  - xterm.js for terminals                           │    │
│  └──────────────────────┬──────────────────────────────┘    │
└─────────────────────────┼───────────────────────────────────┘
                          │ HTTP/REST + WebSocket
┌─────────────────────────┼───────────────────────────────────┐
│  FastAPI Server (apps/web-server)                           │
│  ┌──────────────────────┴──────────────────────────────┐    │
│  │  REST API: /api/projects, /api/tasks, /api/files    │    │
│  │  WebSocket: /ws/terminal, /ws/logs, /ws/progress    │    │
│  │  Static: Serves React SPA build                     │    │
│  └──────────────────────┬──────────────────────────────┘    │
│                         │ subprocess                         │
│  ┌──────────────────────┴──────────────────────────────┐    │
│  │  Existing Backend (apps/backend)                    │    │
│  │  - run.py, spec_runner.py (unchanged)               │    │
│  │  - Claude Agent SDK, Graphiti Memory               │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## Project Structure (New)

```
Auto-Claude/
├── apps/
│   ├── backend/              # UNCHANGED - existing Python CLI
│   ├── frontend/             # DEPRECATED - keep for reference only
│   │
│   ├── frontend-web/         # NEW - React SPA
│   │   ├── src/
│   │   │   ├── components/   # Fork from frontend/src/renderer/components
│   │   │   ├── stores/       # Fork from frontend/src/renderer/stores
│   │   │   ├── lib/
│   │   │   │   ├── api-client.ts      # HTTP client wrapper
│   │   │   │   ├── websocket.ts       # WebSocket manager
│   │   │   │   ├── api-adapter.ts     # API-compatible adapter
│   │   │   │   └── auth.ts            # Token auth
│   │   │   ├── pages/
│   │   │   │   ├── Kanban.tsx
│   │   │   │   ├── Editor.tsx         # NEW - Monaco file editor
│   │   │   │   ├── Terminal.tsx
│   │   │   │   └── ...
│   │   │   ├── App.tsx
│   │   │   └── main.tsx
│   │   ├── package.json
│   │   ├── vite.config.ts
│   │   └── tsconfig.json
│   │
│   └── web-server/           # NEW - FastAPI server
│       ├── server/
│       │   ├── __init__.py
│       │   ├── main.py               # App factory, CORS, static files
│       │   ├── config.py             # Settings (API_TOKEN, HOST, PORT)
│       │   ├── auth.py               # Token middleware
│       │   ├── routes/
│       │   │   ├── projects.py       # Project CRUD
│       │   │   ├── tasks.py          # Task management
│       │   │   ├── workspace.py      # Worktree operations
│       │   │   ├── terminal.py       # Terminal REST endpoints
│       │   │   ├── files.py          # File browser/editor
│       │   │   ├── git.py            # Git operations
│       │   │   ├── settings.py       # App settings
│       │   │   ├── github.py         # GitHub integration
│       │   │   ├── gitlab.py         # GitLab integration
│       │   │   ├── roadmap.py        # Roadmap operations
│       │   │   ├── ideation.py       # Ideation endpoints
│       │   │   ├── changelog.py      # Changelog operations
│       │   │   ├── insights.py       # AI insights chat
│       │   │   └── context.py        # Context/memory
│       │   ├── websockets/
│       │   │   ├── terminal.py       # PTY WebSocket handler
│       │   │   ├── logs.py           # Task log streaming
│       │   │   └── progress.py       # Execution progress streaming
│       │   ├── services/
│       │   │   ├── agent_service.py  # Wraps run.py, spec_runner.py
│       │   │   ├── terminal_service.py # PTY management
│       │   │   ├── file_service.py   # File operations
│       │   │   └── git_service.py    # Git operations
│       │   └── pty/
│       │       ├── manager.py        # PTY session management
│       │       └── session.py        # Individual PTY session
│       ├── requirements.txt
│       └── .env.example
```

---

## Implementation Phases

### Phase 1: Backend API Server Foundation

**Goal:** Create FastAPI server with core endpoints

**Files to Create:**
- `apps/web-server/server/main.py` - FastAPI app with CORS, static files
- `apps/web-server/server/config.py` - Settings from environment
- `apps/web-server/server/auth.py` - Bearer token middleware
- `apps/web-server/requirements.txt`:
  ```
  fastapi>=0.109.0
  uvicorn>=0.27.0
  python-multipart>=0.0.6
  ptyprocess>=0.7.0
  websockets>=12.0
  pydantic>=2.0.0
  python-dotenv>=1.0.0
  ```

**Routes to Implement:**
1. `routes/projects.py` - Project CRUD (list, add, remove, get details)
2. `routes/tasks.py` - Task management (list, create, get, update, delete)
3. `routes/settings.py` - App settings (get, update)
4. `routes/files.py` - File operations (list dir, read, write, search)

**Key Mapping from IPC:**
| IPC Channel | REST Endpoint |
|-------------|---------------|
| `get-projects` | `GET /api/projects` |
| `add-project` | `POST /api/projects` |
| `get-tasks` | `GET /api/projects/{id}/tasks` |
| `create-task` | `POST /api/projects/{id}/tasks` |
| `get-settings` | `GET /api/settings` |
| `save-settings` | `PUT /api/settings` |

---

### Phase 2: Agent Execution & WebSocket Streaming

**Goal:** Run tasks and stream logs/progress in real-time

**Files to Create:**
- `apps/web-server/server/services/agent_service.py` - Wraps run.py/spec_runner.py
- `apps/web-server/server/websockets/logs.py` - Log streaming
- `apps/web-server/server/websockets/progress.py` - Progress streaming

**Implementation:**
```python
# services/agent_service.py (conceptual)
class AgentService:
    async def start_task(self, task_id, spec_dir, project_dir, on_output):
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "run.py", "--spec", spec_id, "--auto-continue",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=project_dir
        )
        async for line in proc.stdout:
            await on_output(task_id, line.decode())
```

**Routes:**
- `POST /api/tasks/{id}/start` - Start task execution
- `POST /api/tasks/{id}/stop` - Stop task
- `GET /api/tasks/{id}/status` - Get execution status

**WebSockets:**
- `WS /ws/tasks/{id}/logs` - Stream task logs
- `WS /ws/tasks/{id}/progress` - Stream execution progress

---

### Phase 3: Terminal WebSocket Backend

**Goal:** Replace node-pty with Python PTY over WebSocket

**Files to Create:**
- `apps/web-server/server/pty/manager.py` - PTY session management
- `apps/web-server/server/pty/session.py` - Individual PTY wrapper
- `apps/web-server/server/websockets/terminal.py` - WebSocket handler
- `apps/web-server/server/routes/terminal.py` - REST for create/destroy

**Implementation:**
```python
# pty/session.py (using ptyprocess)
class PTYSession:
    def __init__(self, session_id, cwd, cols, rows):
        self.pty = PtyProcess.spawn(['/bin/bash', '-l'],
                                     dimensions=(rows, cols), cwd=cwd)

    async def read_output(self):
        return await asyncio.get_event_loop().run_in_executor(
            None, self.pty.read, 1024)

    def write_input(self, data):
        self.pty.write(data)
```

**Endpoints:**
- `POST /api/terminals` - Create terminal session
- `DELETE /api/terminals/{id}` - Close terminal
- `WS /ws/terminal/{id}` - Bidirectional I/O

---

### Phase 4: Frontend Web App

**Goal:** Fork React app, replace IPC with HTTP/WebSocket

**Step 1: Create frontend-web directory**
```bash
mkdir -p apps/frontend-web/src
cp -r apps/frontend/src/renderer/* apps/frontend-web/src/
cp -r apps/frontend/src/shared apps/frontend-web/src/
```

**Step 2: Create API adapter (replaces window.API)**

File: `apps/frontend-web/src/lib/api-adapter.ts`
```typescript
// Matches API interface but uses HTTP/WebSocket
export const webAPI: API = {
  getProjects: async () => {
    const res = await fetch('/api/projects', { headers: authHeaders() });
    return { success: true, data: await res.json() };
  },

  createTask: async (projectId, title, description) => {
    const res = await fetch(`/api/projects/${projectId}/tasks`, {
      method: 'POST',
      headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, description })
    });
    return { success: true, data: await res.json() };
  },

  // Terminal operations use REST + WebSocket
  createTerminal: async (options) => {
    const res = await fetch('/api/terminals', { method: 'POST', ... });
    const terminal = await res.json();
    // WebSocket for I/O handled separately
    return { success: true, data: terminal };
  },

  // Event listeners use WebSocket subscriptions
  onTaskProgress: (callback) => {
    const ws = getWebSocket('progress');
    ws.onmessage = (e) => callback(JSON.parse(e.data));
    return () => ws.close();
  },

  // ... implement all 498 IPC channels
};

// Replace window.API
window.API = webAPI;
```

**Step 3: Update build system**

File: `apps/frontend-web/vite.config.ts`
```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
      '/ws': { target: 'ws://localhost:8000', ws: true }
    }
  },
  build: {
    outDir: '../web-server/static'
  }
});
```

**Step 4: Remove Electron-specific code**
- Delete preload scripts, main process code
- Replace `electron-vite` with `vite`
- Remove `@lydell/node-pty`, `electron-builder`, `electron-updater`

**Reusable Components (95%+):**
- All Zustand stores (just change API calls in actions)
- Kanban board components
- Task detail modals
- Settings dialogs
- GitHub/GitLab UI components
- Roadmap, Changelog, Insights views

---

### Phase 5: Monaco Editor Integration

**Goal:** Full IDE-like file editing experience

**Dependencies:**
```json
"@monaco-editor/react": "^4.6.0"
```

**New Components:**
- `pages/Editor.tsx` - Main editor page
- `components/editor/FileTree.tsx` - File navigation tree
- `components/editor/TabBar.tsx` - Multi-file tabs
- `components/editor/MonacoEditor.tsx` - Editor wrapper
- `components/editor/GitDiff.tsx` - Diff viewer using DiffEditor

**File: `pages/Editor.tsx`**
```typescript
import { Editor, DiffEditor } from '@monaco-editor/react';

export function EditorPage() {
  const [tabs, setTabs] = useState<FileTab[]>([]);
  const [activeTab, setActiveTab] = useState<string | null>(null);

  return (
    <div className="flex h-full">
      <FileTree onFileSelect={openFile} />
      <div className="flex-1 flex flex-col">
        <TabBar tabs={tabs} activeTab={activeTab} onSelect={setActiveTab} />
        <Editor
          language={detectLanguage(activeTab?.path)}
          value={activeTab?.content}
          onChange={handleChange}
          theme="vs-dark"
          options={{ minimap: { enabled: true }, fontSize: 14 }}
        />
      </div>
    </div>
  );
}
```

**Features:**
- File tree with lazy loading (expand on click)
- Multi-tab interface with dirty indicators
- Syntax highlighting for all common languages
- Search within file (Ctrl+F)
- Go to line (Ctrl+G)
- Git diff view for worktree changes

---

### Phase 6: Remaining Feature Parity

**Routes to Complete:**
- `routes/workspace.py` - Worktree merge, discard, diff preview
- `routes/github.py` - All 40+ GitHub operations
- `routes/gitlab.py` - GitLab operations
- `routes/roadmap.py` - Roadmap CRUD and generation
- `routes/ideation.py` - Ideation generation
- `routes/changelog.py` - Changelog operations
- `routes/insights.py` - AI chat interface
- `routes/context.py` - Graphiti memory integration

**WebSocket Events:**
- Roadmap generation progress
- Ideation progress
- Insights chat streaming
- GitHub investigation progress

---

### Phase 7: Testing & Polish

**Testing:**
1. Unit tests for API routes (pytest)
2. WebSocket connection tests
3. E2E tests for critical workflows
4. Cross-browser testing

**Polish:**
1. Error handling (network failures, auth errors)
2. Loading states and skeleton screens
3. Responsive design for mobile access
4. Documentation (API docs via OpenAPI)

---

## Critical Files Reference

**To Study/Modify:**
| File | Purpose |
|------|---------|
| `apps/frontend/src/shared/constants/ipc.ts` | 498 IPC channels to map to REST/WS |
| `apps/frontend/src/shared/types/index.ts` | TypeScript interfaces to reuse |
| `apps/frontend/src/renderer/lib/browser-mock.ts` | API interface template |
| `apps/frontend/src/preload/api/index.ts` | Complete API method signatures |
| `apps/frontend/src/main/terminal/pty-manager.ts` | PTY implementation to port |
| `apps/backend/cli/main.py` | CLI args for subprocess wrapping |
| `apps/backend/run.py` | Entry point for task execution |

---

## Authentication

**Simple Token Auth:**
```python
# config.py
API_TOKEN = os.getenv("AUTO_CLAUDE_TOKEN", "change-me")

# auth.py middleware
async def dispatch(request, call_next):
    if request.url.path.startswith("/api"):
        auth = request.headers.get("Authorization")
        if auth != f"Bearer {settings.API_TOKEN}":
            return JSONResponse({"error": "Unauthorized"}, 401)
    return await call_next(request)
```

**WebSocket Auth:**
```python
@router.websocket("/ws/terminal/{id}")
async def terminal_ws(websocket, id):
    token = websocket.query_params.get("token")
    if token != settings.API_TOKEN:
        await websocket.close(4001, "Unauthorized")
        return
    await websocket.accept()
```

**Frontend:**
```typescript
const token = localStorage.getItem('auto-claude-token');
const headers = { Authorization: `Bearer ${token}` };
```

---

## Deployment Notes

**Development:**
```bash
# Terminal 1: Backend server
cd apps/web-server && uvicorn server.main:app --reload --port 8000

# Terminal 2: Frontend dev server
cd apps/frontend-web && npm run dev
```

**Production:**
```bash
# Build frontend
cd apps/frontend-web && npm run build

# Run server (serves static files + API)
cd apps/web-server && uvicorn server.main:app --host 0.0.0.0 --port 8000
```

**Remote Access:**
- Run behind nginx/caddy reverse proxy with HTTPS
- Or use SSH tunnel: `ssh -L 8000:localhost:8000 your-server`
- Or use Cloudflare Tunnel / ngrok for quick access

---

## Summary

| Phase | Deliverable |
|-------|-------------|
| 1 | FastAPI server + core routes |
| 2 | Agent execution + log streaming |
| 3 | Terminal WebSocket backend |
| 4 | Frontend web app |
| 5 | Monaco editor integration |
| 6 | Feature parity (GitHub, Roadmap, etc.) |
| 7 | Testing & polish |
