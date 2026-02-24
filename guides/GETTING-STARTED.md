# Claude Code Manager Web - Getting Started

Welcome to **Claude Code Manager Web**! This guide will walk you through installation, first-run configuration, and creating your first AI-powered coding task.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [First-Run Configuration](#first-run-configuration)
4. [Accessing the Web Interface](#accessing-the-web-interface)
5. [Creating Your First Project](#creating-your-first-project)
6. [Running Your First AI Task](#running-your-first-ai-task)
7. [Understanding the Interface](#understanding-the-interface)
8. [Next Steps](#next-steps)

---

## Prerequisites

Before installing Claude Code Manager Web, ensure you have the following:

### Required Software

| Software | Minimum Version | Purpose |
|----------|-----------------|---------|
| **Node.js** | 24.0.0+ | Frontend build and runtime |
| **npm** | 10.0.0+ | Package management |
| **Python** | 3.12+ | Backend agents and server |
| **Git** | 2.30+ | Version control and worktree management |

### Check Your Versions

```bash
# Check Node.js and npm
node --version    # Should output v24.x.x or higher
npm --version     # Should output 10.x.x or higher

# Check Python
python3 --version # Should output Python 3.12.x or higher

# Check Git
git --version     # Should output 2.30.x or higher
```

### Installing Prerequisites

If you don't have the required software, follow these installation steps:

#### Node.js 24+

**Windows:**
```bash
# Using winget
winget install OpenJS.NodeJS.LTS
```

**macOS:**
```bash
# Using Homebrew
brew install node
```

**Linux (Ubuntu/Debian):**
```bash
# Using NodeSource
curl -fsSL https://deb.nodesource.com/setup_24.x | sudo -E bash -
sudo apt-get install -y nodejs
```

#### Python 3.12+

**Windows:**
```bash
winget install Python.Python.3.12
```

**macOS:**
```bash
brew install python@3.12
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt install python3.12 python3.12-venv python3.12-dev
```

**Linux (Fedora):**
```bash
sudo dnf install python3.12
```

### Claude Code OAuth Token

You'll need an OAuth token from the Claude Code CLI:

```bash
# Install Claude Code CLI globally
npm install -g @anthropic-ai/claude-code

# Authenticate and obtain your token
claude setup-token
```

Follow the prompts to authenticate with your Anthropic account. Your token will be saved and displayed for use in configuration.

---

## Installation

### Step 1: Clone the Repository

```bash
# Clone the project
git clone https://github.com/dataseeek/Claude-Code-Manager-Web.git

# Navigate to the project directory
cd Claude-Code-Manager-Web
```

### Step 2: Install All Dependencies

The project includes a convenient script to install all dependencies at once:

```bash
npm run install:all
```

This command installs:
- Root package dependencies
- Frontend dependencies (`apps/frontend-web/`)
- Web server dependencies (`apps/web-server/`)
- Backend agent dependencies (`apps/backend/`)

> **Note:** This may take a few minutes on first run as it sets up Python virtual environments and installs all npm packages.

### Step 3: Verify Installation

```bash
# Check that virtual environments were created
ls apps/web-server/.venv
ls apps/backend/.venv
```

---

## First-Run Configuration

### Step 1: Create Environment Files

```bash
# Copy the example environment files
cp apps/backend/.env.example apps/backend/.env
cp apps/web-server/.env.example apps/web-server/.env
```

### Step 2: Configure the Backend (apps/backend/.env)

Open `apps/backend/.env` in your preferred editor and configure:

```bash
# Required: Your Claude Code OAuth token
CLAUDE_CODE_OAUTH_TOKEN=your-oauth-token-here

# Optional: Enable Graphiti memory for cross-session learning
GRAPHITI_ENABLED=true

# Optional: Integration tokens (if using GitHub/Linear features)
# GITHUB_TOKEN=your-github-token
# LINEAR_API_KEY=your-linear-api-key
```

### Step 3: Configure the Web Server (apps/web-server/.env)

Open `apps/web-server/.env` and verify or customize:

```bash
# Server binding (0.0.0.0 allows remote access)
AUTO_CLAUDE_HOST=0.0.0.0
AUTO_CLAUDE_PORT=8000

# Enable debug mode for development
AUTO_CLAUDE_DEBUG=true

# API token is auto-generated if not set
# AUTO_CLAUDE_API_TOKEN=your-custom-token
```

### Step 4: Start the Servers

You'll need **two terminal windows** to run the application:

#### Terminal 1 - Backend Web Server

```bash
# Navigate to the web server
cd apps/web-server

# Activate the Python virtual environment
source .venv/bin/activate  # Linux/macOS
# OR
.venv\Scripts\activate     # Windows

# Start the server
python -m server.main
```

You should see output like:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     API Token: abc123...
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

> **Important:** Note the API Token displayed in the console. You'll need this to access the web interface. The token is also saved to `~/.auto-claude-web/.token`.

#### Terminal 2 - Frontend Development Server

```bash
# Navigate to the frontend
cd apps/frontend-web

# Start the development server
npm run dev
```

You should see:
```
  VITE v7.x.x  ready in xxx ms

  -> Local:   http://localhost:5173/
  -> Network: http://xxx.xxx.xxx.xxx:5173/
```

---

## Accessing the Web Interface

### Step 1: Open the Application

Open your web browser and navigate to:

```
http://localhost:5173
```

### Step 2: Enter the API Token

On first access, you'll see a login screen asking for your API token.

1. Copy the token from your Terminal 1 output (where you started the web server)
2. Or read it from `~/.auto-claude-web/.token`:
   ```bash
   cat ~/.auto-claude-web/.token
   ```
3. Paste the token and click "Connect"

### Step 3: Welcome Screen

After authentication, you'll see the welcome screen. From here you can:
- Create a new project
- Access application settings
- View documentation links

---

## Creating Your First Project

### Step 1: Add a Project

Click **"Add Project"** or use the **+** button in the project tab bar.

### Step 2: Select Project Directory

A file browser dialog will appear. Navigate to and select the root directory of an existing Git repository you want to work with.

> **Important:** Claude Code Manager Web works with existing Git repositories. Make sure your project:
> - Is a Git repository (`git init` has been run)
> - Has at least one commit
> - Has a clean working directory (or you're okay with the current state)

### Step 3: Configure Project Name

Give your project a meaningful name (optional - defaults to the directory name).

### Step 4: Project Initialization

The system will:
1. Index your project structure
2. Create the `.auto-claude/` directory for task data
3. Load any existing tasks (if any)

You'll now see your project tab in the tab bar and the Kanban board view.

---

## Running Your First AI Task

### Step 1: Create a New Task

From the Kanban board, click the **"+ New Task"** button (or press `N`).

### Step 2: Task Creation Wizard

The **Task Creation Wizard** will guide you through:

#### Enter Task Description

Describe what you want the AI to implement. Be specific and clear:

**Good examples:**
- "Add a dark mode toggle to the settings page with system preference detection"
- "Create a user registration form with email validation and password strength indicator"
- "Fix the bug where the login button is disabled after a failed attempt"

**Less effective examples:**
- "Make it better" (too vague)
- "Add everything" (no clear scope)

#### Review Generated Spec

The AI will analyze your request and generate a specification including:
- **Summary** - What will be implemented
- **Acceptance Criteria** - How success will be measured
- **Complexity Assessment** - Estimated effort (simple/standard/complex)

#### Confirm or Edit

Review the generated spec. You can:
- **Accept** - Proceed with the generated spec
- **Edit** - Modify the spec before proceeding
- **Regenerate** - Ask the AI to rewrite the spec

### Step 3: Start the Task

Once your task is created, it appears in the **Backlog** column of the Kanban board.

To start AI implementation:
1. Click on the task card to open the **Task Detail Modal**
2. Click **"Start Task"**
3. Choose options:
   - **Model** - Select the Claude model (default: claude-sonnet-4)
   - **Profile** - Select execution profile (default: standard)

### Step 4: Monitor Progress

Watch the task progress through the AI pipeline:

```
Backlog → In Progress → AI Review → Human Review → Done
```

**During execution, you can:**
- View real-time progress in the Task Detail Modal
- Watch agent logs and outputs
- Open the terminal view to see agent activity
- Pause or stop execution if needed

### Step 5: Review and Merge

When the task reaches **Human Review**:

1. Click the task to open details
2. Review the changes in the **Code Review** tab
3. Test the implementation in the task's worktree:
   ```bash
   cd .auto-claude/worktrees/tasks/YOUR-TASK-ID/
   # Run your project's test/build commands
   npm run dev  # or your project's command
   ```
4. If satisfied, click **"Merge"** to merge changes to your main branch
5. If changes needed, add feedback and click **"Request Changes"**

---

## Understanding the Interface

### Sidebar Navigation

| Icon | View | Description |
|------|------|-------------|
| **Board** | Kanban | Task board with drag-and-drop management |
| **Terminal** | Terminals | Multi-terminal grid with PTY support |
| **Code** | Editor | Monaco code editor with file browser |
| **Branch** | Worktrees | Git worktree management and merge operations |
| **Map** | Roadmap | AI-generated feature roadmap |
| **Lightbulb** | Ideation | AI-powered feature brainstorming |
| **Database** | Context | Project indexing and memory management |
| **GitHub** | Issues | GitHub issue integration |
| **GitLab** | GitLab | GitLab issue integration |
| **PR** | Pull Requests | AI-powered PR review |
| **History** | Changelog | Automatic changelog generation |
| **Chart** | Insights | AI analysis and project metrics |
| **Settings** | Settings | Application configuration |

### Task Statuses

| Status | Meaning |
|--------|---------|
| **Backlog** | Task created, waiting to start |
| **In Progress** | AI agents actively working |
| **AI Review** | QA agent reviewing implementation |
| **Human Review** | Ready for your review and merge |
| **Done** | Completed and merged |

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `N` | New task (from Kanban) |
| `T` | New terminal |
| `Esc` | Close modals |
| `Ctrl+K` | Command palette |

---

## Next Steps

Congratulations! You've completed your first task with Claude Code Manager Web. Here's what to explore next:

### Explore More Features

- **[Web UI Guide](WEB-UI-GUIDE.md)** - Deep dive into all views and features
- **[Task Workflow](TASK-WORKFLOW.md)** - Understand the complete task lifecycle
- **[CLI Usage](CLI-USAGE.md)** - Power user terminal workflows

### Configuration & Customization

- **[Configuration](CONFIGURATION.md)** - All environment variables and settings
- **[Troubleshooting](TROUBLESHOOTING.md)** - Common issues and solutions

### For Developers

- **[Development Setup](DEVELOPMENT-SETUP.md)** - Setting up a development environment
- **[Architecture](ARCHITECTURE.md)** - System design and component interactions
- **[API Reference](API-REFERENCE.md)** - REST and WebSocket API documentation

### Get Help

- **GitHub Issues:** [Report bugs or request features](https://github.com/dataseeek/Claude-Code-Manager-Web/issues)
- **GitHub Discussions:** [Ask questions and share ideas](https://github.com/dataseeek/Claude-Code-Manager-Web/discussions)

---

## Quick Reference

### Start the Application

```bash
# Terminal 1: Backend
cd apps/web-server && source .venv/bin/activate && python -m server.main

# Terminal 2: Frontend
cd apps/frontend-web && npm run dev
```

### Access Points

| Service | URL |
|---------|-----|
| Web Interface | http://localhost:5173 |
| API Server | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |

### Key Files

| File | Purpose |
|------|---------|
| `~/.auto-claude-web/.token` | API authentication token |
| `~/.auto-claude-web/settings.json` | Application settings |
| `apps/backend/.env` | Backend configuration |
| `apps/web-server/.env` | Web server configuration |
| `.auto-claude/specs/` | Task specifications |
| `.auto-claude/worktrees/` | Isolated task worktrees |

---

**Claude Code Manager Web** - Get started building with AI agents!
