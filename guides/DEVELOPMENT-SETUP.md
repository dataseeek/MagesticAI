# Claude Code Manager Web - Development Setup Guide

This guide provides detailed instructions for setting up a development environment to contribute to Claude Code Manager Web. It covers all three applications, debugging configurations, hot reload, and IDE recommendations.

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Project Structure](#project-structure)
4. [Frontend Development (frontend-web)](#frontend-development-frontend-web)
5. [Web Server Development (web-server)](#web-server-development-web-server)
6. [Backend Agent Development (backend)](#backend-agent-development-backend)
7. [Debugging Configurations](#debugging-configurations)
8. [Hot Reload](#hot-reload)
9. [IDE Recommendations](#ide-recommendations)
10. [Running All Components](#running-all-components)
11. [Testing](#testing)
12. [Common Development Tasks](#common-development-tasks)
13. [Environment Variables Reference](#environment-variables-reference)

---

## Overview

Claude Code Manager Web consists of three main applications:

| Application | Technology | Port | Purpose |
|-------------|------------|------|---------|
| **frontend-web** | React 19 + Vite | 5173 | Web-based user interface |
| **web-server** | FastAPI + Python | 8000 | REST API and WebSocket server |
| **backend** | Python | N/A | AI agent system (Planner, Coder, QA) |

The frontend communicates with the web server via REST API and WebSocket connections. The web server orchestrates backend agents for AI-powered task execution.

---

## Prerequisites

### Required Software

| Software | Version | Installation Check |
|----------|---------|-------------------|
| **Node.js** | 24.0.0+ | `node --version` |
| **npm** | 10.0.0+ | `npm --version` |
| **Python** | 3.12+ | `python3 --version` |
| **Git** | 2.30+ | `git --version` |

### Platform-Specific Installation

#### macOS

```bash
# Using Homebrew
brew install node@24 python@3.12 git
```

#### Ubuntu/Debian

```bash
# Node.js 24
curl -fsSL https://deb.nodesource.com/setup_24.x | sudo -E bash -
sudo apt-get install -y nodejs

# Python 3.12
sudo apt install python3.12 python3.12-venv python3.12-dev

# Git
sudo apt install git
```

#### Windows

```bash
# Using winget
winget install OpenJS.NodeJS.LTS
winget install Python.Python.3.12
winget install Git.Git
```

---

## Project Structure

```
Claude-Code-Manager-Web/
├── apps/
│   ├── frontend-web/          # React frontend application
│   │   ├── src/               # Source code
│   │   │   ├── components/    # React components
│   │   │   ├── pages/         # Page components
│   │   │   ├── stores/        # Zustand state stores
│   │   │   ├── hooks/         # Custom React hooks
│   │   │   └── lib/           # Utilities and API client
│   │   ├── public/            # Static assets
│   │   ├── vite.config.ts     # Vite configuration
│   │   └── package.json
│   │
│   ├── web-server/            # FastAPI backend server
│   │   ├── server/
│   │   │   ├── main.py        # App entry point
│   │   │   ├── config.py      # Settings management
│   │   │   ├── routes/        # REST API routes
│   │   │   ├── websockets/    # WebSocket handlers
│   │   │   └── services/      # Business logic
│   │   ├── static/            # Built frontend (production)
│   │   ├── requirements.txt
│   │   └── .env.example
│   │
│   └── backend/               # AI Agent system
│       ├── agents/            # Agent implementations
│       ├── core/              # Core utilities
│       ├── cli/               # CLI commands
│       ├── requirements.txt
│       └── .env.example
│
├── tests/                     # Test suites
├── scripts/                   # Build and utility scripts
├── guides/                    # Documentation (you are here)
└── package.json               # Root package with workspace scripts
```

---

## Frontend Development (frontend-web)

The frontend is built with **React 19**, **Vite 7**, **TypeScript**, and **Tailwind CSS 4**.

### Setup

```bash
# Navigate to frontend directory
cd apps/frontend-web

# Install dependencies
npm install

# Start development server
npm run dev
```

### Available Scripts

| Script | Command | Description |
|--------|---------|-------------|
| `dev` | `npm run dev` | Start Vite dev server with HMR |
| `build` | `npm run build` | Build for production |
| `preview` | `npm run preview` | Preview production build |
| `lint` | `npm run lint` | Run ESLint |
| `typecheck` | `npm run typecheck` | Run TypeScript compiler |

### Key Technologies

| Technology | Version | Purpose |
|------------|---------|---------|
| React | 19.x | UI framework |
| Vite | 7.x | Build tool and dev server |
| TypeScript | 5.x | Type safety |
| Tailwind CSS | 4.x | Utility-first CSS |
| Zustand | 5.x | State management |
| Monaco Editor | 4.x | Code editor |
| xterm.js | 6.x | Terminal emulation |
| Radix UI | 1.x | Accessible UI primitives |

### Directory Structure

```
src/
├── components/
│   ├── ui/                    # Shadcn/UI components
│   ├── kanban/                # Kanban board components
│   ├── terminal/              # Terminal components
│   ├── editor/                # Code editor components
│   └── ...
├── pages/                     # Route page components
├── stores/                    # Zustand state stores
│   ├── useProjectStore.ts     # Project state
│   ├── useTaskStore.ts        # Task state
│   ├── useTerminalStore.ts    # Terminal state
│   └── ...
├── hooks/                     # Custom React hooks
├── lib/
│   ├── api-client.ts          # API client wrapper
│   └── utils.ts               # Utility functions
└── App.tsx                    # Root component
```

### Path Aliases

The project uses path aliases defined in `vite.config.ts` and `tsconfig.json`:

```typescript
// In your code, use:
import { Button } from '@components/ui/button';
import { useProjectStore } from '@stores/useProjectStore';
import { cn } from '@lib/utils';
```

| Alias | Path |
|-------|------|
| `@` | `./src` |
| `@components` | `./src/components` |
| `@lib` | `./src/lib` |
| `@stores` | `./src/stores` |
| `@pages` | `./src/pages` |
| `@hooks` | `./src/hooks` |

### Environment Variables

Create `.env.local` for local overrides (not committed):

```bash
# Override API URL (default uses Vite proxy)
VITE_API_URL=http://localhost:8000

# Override WebSocket URL
VITE_WS_URL=ws://localhost:8000
```

---

## Web Server Development (web-server)

The web server is built with **FastAPI** and provides REST API and WebSocket endpoints.

### Setup

```bash
# Navigate to web server directory
cd apps/web-server

# Create Python virtual environment
python3.12 -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # Linux/macOS
# OR
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Start development server
python -m server.main
```

### Configuration (.env)

```bash
# Server settings
APP_HOST=0.0.0.0        # Listen on all interfaces
APP_PORT=8000           # Server port
APP_DEBUG=true          # Enable debug mode (required for API docs)

# Authentication (auto-generated if not set)
# APP_API_TOKEN=your-secure-token

# CORS origins (frontend URLs allowed to connect)
APP_CORS_ORIGINS=["http://localhost:5173", "http://localhost:3000"]

# Paths (auto-detected if not set)
# APP_BACKEND_PATH=/path/to/apps/backend
# APP_PROJECTS_DATA_DIR=/path/to/data

# Terminal settings
APP_DEFAULT_SHELL=/bin/bash
APP_MAX_TERMINALS=20

# Task execution
APP_MAX_CONCURRENT_TASKS=5
```

### Project Structure

```
apps/web-server/
├── server/
│   ├── main.py                # FastAPI app entry, lifespan events
│   ├── config.py              # Pydantic settings management
│   ├── auth.py                # Token authentication
│   ├── routes/
│   │   ├── projects.py        # /api/projects endpoints
│   │   ├── tasks.py           # /api/tasks endpoints
│   │   ├── files.py           # /api/files endpoints
│   │   ├── settings.py        # /api/settings endpoints
│   │   ├── terminal.py        # /api/terminals endpoints
│   │   ├── github.py          # /api/github endpoints
│   │   ├── gitlab.py          # /api/gitlab endpoints
│   │   └── ...
│   ├── websockets/
│   │   ├── events.py          # /ws/events global broadcast
│   │   ├── terminal.py        # /ws/terminal/{id} PTY I/O
│   │   ├── logs.py            # /ws/tasks/{id}/logs streaming
│   │   └── progress.py        # /ws/tasks/{id}/progress updates
│   └── services/
│       └── ...                # Business logic services
├── static/                    # Built frontend (production)
├── tests/                     # Web server tests
├── requirements.txt
└── .env.example
```

### API Documentation

When `APP_DEBUG=true`, API documentation is available at:

| URL | Documentation |
|-----|---------------|
| http://localhost:8000/docs | Swagger UI (interactive) |
| http://localhost:8000/redoc | ReDoc (readable) |

### Running with Auto-Reload

```bash
# The server auto-reloads when DEBUG is enabled
APP_DEBUG=true python -m server.main
```

For manual uvicorn control with specific reload options:

```bash
# Activate virtual environment first
source .venv/bin/activate

# Run with uvicorn directly
uvicorn server.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Backend Agent Development (backend)

The backend contains the AI agent system (Planner, Coder, QA agents) that implements coding tasks.

### Setup

```bash
# Navigate to backend directory
cd apps/backend

# Create Python virtual environment
python3.12 -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # Linux/macOS
# OR
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
```

### Configuration (.env)

The backend requires authentication with Claude Code:

```bash
# Required: Claude Code OAuth Token
CLAUDE_CODE_OAUTH_TOKEN=your-oauth-token-here
# Get your token: claude setup-token

# Optional: Custom API endpoint (for proxies)
# ANTHROPIC_BASE_URL=http://127.0.0.1:3456

# Optional: Model override
# AUTO_BUILD_MODEL=claude-opus-4-5-20251101

# Debug mode
DEBUG=true
DEBUG_LEVEL=2  # 1=basic, 2=detailed, 3=verbose

# Optional: Log to file
# DEBUG_LOG_FILE=debug.log

# Graphiti Memory (optional)
GRAPHITI_ENABLED=true
# GRAPHITI_LLM_PROVIDER=openai
# OPENAI_API_KEY=sk-xxxxxxxx
```

### Project Structure

```
apps/backend/
├── agents/
│   ├── planner.py             # Planning agent
│   ├── coder.py               # Coding agent
│   ├── qa_reviewer.py         # QA review agent
│   ├── spec_writer.py         # Spec generation agent
│   └── ...
├── core/
│   ├── runner.py              # Agent execution runner
│   ├── worktree.py            # Git worktree management
│   └── ...
├── cli/
│   ├── main.py                # CLI entry point
│   └── ...
├── context/                   # Project context management
├── analysis/                  # Code analysis tools
├── debug.py                   # Debug utilities
└── requirements.txt
```

### Running Agents Directly (CLI)

The backend can be run directly via CLI for testing:

```bash
# Activate virtual environment
source .venv/bin/activate

# Run a task (from project root with .auto-claude directory)
python -m cli.main start-task TASK_ID

# Run specific agent
python -m agents.planner --task-id TASK_ID
```

---

## Debugging Configurations

### VS Code Setup

Create `.vscode/launch.json` in the project root:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Frontend: Chrome",
      "type": "chrome",
      "request": "launch",
      "url": "http://localhost:5173",
      "webRoot": "${workspaceFolder}/apps/frontend-web/src",
      "sourceMapPathOverrides": {
        "webpack:///./src/*": "${webRoot}/*"
      }
    },
    {
      "name": "Web Server: FastAPI",
      "type": "debugpy",
      "request": "launch",
      "module": "server.main",
      "cwd": "${workspaceFolder}/apps/web-server",
      "env": {
        "APP_DEBUG": "true"
      },
      "console": "integratedTerminal"
    },
    {
      "name": "Backend: Agent Runner",
      "type": "debugpy",
      "request": "launch",
      "module": "cli.main",
      "args": ["start-task", "${input:taskId}"],
      "cwd": "${workspaceFolder}/apps/backend",
      "env": {
        "DEBUG": "true",
        "DEBUG_LEVEL": "2"
      },
      "console": "integratedTerminal"
    }
  ],
  "inputs": [
    {
      "id": "taskId",
      "type": "promptString",
      "description": "Task ID to run"
    }
  ],
  "compounds": [
    {
      "name": "Full Stack",
      "configurations": ["Frontend: Chrome", "Web Server: FastAPI"]
    }
  ]
}
```

### VS Code Settings

Create `.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": "./apps/backend/.venv/bin/python",
  "python.analysis.extraPaths": [
    "./apps/backend",
    "./apps/web-server"
  ],
  "typescript.tsdk": "apps/frontend-web/node_modules/typescript/lib",
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "esbenp.prettier-vscode",
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter",
    "editor.formatOnSave": true
  },
  "[typescript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },
  "[typescriptreact]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  }
}
```

### PyCharm / IntelliJ Setup

1. **Mark directories as Sources Root:**
   - `apps/backend` - Sources Root
   - `apps/web-server` - Sources Root

2. **Configure Python Interpreter:**
   - Each app should use its own virtual environment
   - `apps/backend/.venv/bin/python`
   - `apps/web-server/.venv/bin/python`

3. **Run Configuration for Web Server:**
   - Script path: `-m server.main`
   - Working directory: `apps/web-server`
   - Environment variables: `APP_DEBUG=true`

### Chrome DevTools

For frontend debugging:

1. Open `http://localhost:5173` in Chrome
2. Open DevTools (`F12` or `Cmd+Option+I`)
3. Use the **Sources** tab to set breakpoints
4. React DevTools extension for component inspection
5. Network tab for API request inspection

### Backend Debug Mode

Enable detailed logging in the backend:

```bash
# In apps/backend/.env
DEBUG=true
DEBUG_LEVEL=3  # Verbose logging

# Debug specific components
# DEBUG_LOG_FILE=debug.log  # Log to file
```

---

## Hot Reload

### Frontend (Vite HMR)

The frontend uses Vite's Hot Module Replacement (HMR) out of the box:

```bash
cd apps/frontend-web
npm run dev
```

- **React components** update without full page reload
- **CSS changes** apply instantly
- **TypeScript errors** show in the terminal and browser overlay

### Web Server (Uvicorn Reload)

FastAPI uses uvicorn's built-in reload:

```bash
cd apps/web-server
source .venv/bin/activate
python -m server.main  # Auto-reloads when DEBUG=true
```

Reload triggers on:
- Any `.py` file change in `server/` directory
- Configuration file changes

### Backend Agents

The backend agents don't have hot reload (they run as separate processes). For development:

```bash
# Make changes to agent code
# Restart the agent process manually
python -m cli.main start-task TASK_ID
```

---

## IDE Recommendations

### Recommended IDEs

| IDE | Best For | Key Extensions |
|-----|----------|----------------|
| **VS Code** | Full-stack development | ESLint, Prettier, Python, Tailwind CSS IntelliSense |
| **WebStorm** | Frontend development | Built-in TypeScript, React support |
| **PyCharm** | Backend development | Python debugging, testing |
| **Cursor** | AI-assisted development | Built-in AI features |

### VS Code Extensions

Install these extensions for the best experience:

#### Essential

```
dbaeumer.vscode-eslint
esbenp.prettier-vscode
ms-python.python
ms-python.vscode-pylance
bradlc.vscode-tailwindcss
```

#### Recommended

```
ms-python.black-formatter
formulahendry.auto-rename-tag
christian-kohler.path-intellisense
prisma.prisma
eamodio.gitlens
```

### Workspace Setup

Create a multi-root workspace for better organization:

`.vscode/claude-code-manager.code-workspace`:

```json
{
  "folders": [
    {
      "name": "Root",
      "path": ".."
    },
    {
      "name": "Frontend",
      "path": "../apps/frontend-web"
    },
    {
      "name": "Web Server",
      "path": "../apps/web-server"
    },
    {
      "name": "Backend",
      "path": "../apps/backend"
    }
  ],
  "settings": {
    "files.exclude": {
      "**/node_modules": true,
      "**/.venv": true,
      "**/__pycache__": true
    }
  }
}
```

---

## Running All Components

### Quick Start (Two Terminals)

**Terminal 1: Web Server**
```bash
cd apps/web-server
source .venv/bin/activate
python -m server.main
```

**Terminal 2: Frontend**
```bash
cd apps/frontend-web
npm run dev
```

Access the application at `http://localhost:5173`

### Using npm Scripts (Root Directory)

```bash
# Install all dependencies (first time)
npm run install:all

# Start frontend development
npm run dev

# Build for production
npm run build
```

### Production Build

```bash
# Build frontend (outputs to apps/web-server/static/)
cd apps/frontend-web
npm run build

# Run web server (serves static files)
cd apps/web-server
source .venv/bin/activate
python -m server.main
```

---

## Testing

### Frontend Tests

```bash
cd apps/frontend-web

# Run tests
npm test

# Run tests in watch mode
npm run test -- --watch

# Run type checking
npm run typecheck

# Run linting
npm run lint
```

### Web Server Tests

```bash
cd apps/web-server
source .venv/bin/activate

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=server
```

### Backend Tests

```bash
cd apps/backend
source .venv/bin/activate

# Run all tests from project root
pytest ../../tests/ -v

# Skip slow tests
pytest ../../tests/ -m "not slow"

# Run specific test file
pytest ../../tests/test_security.py -v
```

### Running All Tests

```bash
# From project root
npm run test           # Frontend tests
npm run test:backend   # Backend tests
```

---

## Common Development Tasks

### Adding a New API Endpoint

1. **Create route handler** in `apps/web-server/server/routes/`:

```python
# apps/web-server/server/routes/new_feature.py
from fastapi import APIRouter, Depends
from ..auth import verify_token

router = APIRouter(prefix="/api/new-feature", tags=["new-feature"])

@router.get("/")
async def get_feature(token: str = Depends(verify_token)):
    return {"message": "Hello from new feature"}
```

2. **Register route** in `apps/web-server/server/main.py`:

```python
from .routes import new_feature
app.include_router(new_feature.router)
```

3. **Add frontend API call** in `apps/frontend-web/src/lib/api-client.ts`

### Adding a New React Component

1. Create component in `apps/frontend-web/src/components/`
2. Use TypeScript interfaces for props
3. Use existing UI components from `@components/ui/`
4. Follow the functional component pattern with hooks

### Adding a New Agent

1. Create agent file in `apps/backend/agents/`
2. Inherit from base agent class
3. Implement required methods
4. Register in the runner if needed

### Modifying Environment Configuration

1. Update `.env.example` files with new variables
2. Update `config.py` (web-server) or relevant config file
3. Document in this guide's Environment Variables section

---

## Environment Variables Reference

### Web Server (apps/web-server/.env)

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_HOST` | `0.0.0.0` | Server bind address |
| `APP_PORT` | `8000` | Server port |
| `APP_DEBUG` | `false` | Enable debug mode and API docs |
| `APP_API_TOKEN` | Auto-generated | Authentication token |
| `APP_CORS_ORIGINS` | `["http://localhost:5173"]` | Allowed CORS origins |
| `APP_DEFAULT_SHELL` | `/bin/bash` | Default terminal shell |
| `APP_MAX_TERMINALS` | `20` | Maximum terminal sessions |
| `APP_MAX_CONCURRENT_TASKS` | `5` | Maximum parallel tasks |

### Backend (apps/backend/.env)

| Variable | Default | Description |
|----------|---------|-------------|
| `CLAUDE_CODE_OAUTH_TOKEN` | Required | Claude Code authentication |
| `ANTHROPIC_BASE_URL` | - | Custom API endpoint |
| `AUTO_BUILD_MODEL` | `claude-opus-4-5-20251101` | Model override |
| `DEBUG` | `false` | Enable debug logging |
| `DEBUG_LEVEL` | `1` | Debug verbosity (1-3) |
| `DEBUG_LOG_FILE` | - | Log file path |
| `GRAPHITI_ENABLED` | `true` | Enable memory system |
| `DEFAULT_BRANCH` | Auto-detected | Default git branch |

### Frontend (apps/frontend-web/.env.local)

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | Via Vite proxy | Backend API URL |
| `VITE_WS_URL` | Via Vite proxy | WebSocket URL |

---

## Getting Help

- **Issues:** [GitHub Issues](https://github.com/dataseeek/Claude-Code-Manager-Web/issues)
- **Discussions:** [GitHub Discussions](https://github.com/dataseeek/Claude-Code-Manager-Web/discussions)
- **Contributing Guide:** [CONTRIBUTING.md](../CONTRIBUTING.md)
- **Technical Docs:** [DOCS.md](../DOCS.md)

---

**Happy coding!** If you have questions or suggestions for improving this guide, please open an issue or pull request.
