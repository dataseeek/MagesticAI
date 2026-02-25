# MagesticAI - CLI Usage

This guide covers command-line usage for power users, headless server operations, and script automation. While the **Web UI** provides a comprehensive visual experience, the CLI offers direct control over all backend operations.

---

## When to Use CLI

| Use Case | Description |
|----------|-------------|
| **Power User Workflows** | Quick task creation without leaving the terminal |
| **Headless Servers** | Running on remote servers without browser access |
| **CI/CD Integration** | Automating task creation and execution in pipelines |
| **Scripting** | Batch operations or custom automation workflows |
| **Debugging** | Direct access to agent execution for troubleshooting |

---

## Prerequisites

- **Python 3.12+**
- **Claude Code CLI** (`npm install -g @anthropic-ai/claude-code`)
- **Git** (for repository operations)
- **Claude Code OAuth Token** (run `claude setup-token` to obtain)

### Installing Python 3.12+

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
sudo apt install python3.12 python3.12-venv
```

**Linux (Fedora):**
```bash
sudo dnf install python3.12
```

---

## Setup

### Step 1: Navigate to the Backend Directory

```bash
cd apps/backend
```

### Step 2: Set Up Python Environment

**Using uv (Recommended):**
```bash
uv venv && uv pip install -r requirements.txt
```

**Using Standard Python:**
```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
```

### Step 3: Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Get your OAuth token (if you haven't already)
claude setup-token

# Edit apps/backend/.env and add:
# CLAUDE_CODE_OAUTH_TOKEN=your-token-here
```

---

## Creating Specs

All spec-related commands should be run from the `apps/backend/` directory:

```bash
# Activate the virtual environment (if not already active)
source .venv/bin/activate
```

### Interactive Spec Creation

```bash
# Create a spec interactively with prompts
python spec_runner.py --interactive
```

### Spec from Task Description

```bash
# Create a spec with a task description
python spec_runner.py --task "Add user authentication with OAuth"

# Force a specific complexity level
python spec_runner.py --task "Fix button color" --complexity simple

# Continue an interrupted spec
python spec_runner.py --continue 001-feature
```

### Complexity Tiers

The spec runner automatically assesses task complexity:

| Tier | Phases | When Used |
|------|--------|-----------|
| **SIMPLE** | 3 | 1-2 files, single service, no integrations (UI fixes, text changes) |
| **STANDARD** | 6 | 3-10 files, 1-2 services, minimal integrations (features, bug fixes) |
| **COMPLEX** | 8 | 10+ files, multiple services, external integrations |

---

## Running Builds

Run builds from the `apps/backend/` directory:

```bash
# List all specs and their status
python run.py --list

# Run a specific spec
python run.py --spec 001
python run.py --spec 001-feature-name

# Limit iterations for testing
python run.py --spec 001 --max-iterations 5
```

---

## QA Validation

After all subtasks are complete, QA validation runs automatically:

```bash
# Skip automatic QA
python run.py --spec 001 --skip-qa

# Run QA validation manually
python run.py --spec 001 --qa

# Check QA status
python run.py --spec 001 --qa-status
```

### QA Validation Loop

1. **QA Reviewer** checks all acceptance criteria
2. If issues found → creates `QA_FIX_REQUEST.md`
3. **QA Fixer** applies fixes
4. Loop repeats until approved (up to 50 iterations)

---

## Workspace Management

MagesticAI uses Git worktrees for isolated builds. Each task gets its own worktree in the `.magestic-ai/worktrees/` directory.

### Testing in a Worktree

```bash
# Navigate to the task's worktree
cd .magestic-ai/worktrees/tasks/001-feature-name/

# Test the feature using your project's commands
npm run dev  # or your project's run command
```

### Managing Worktrees from CLI

```bash
# Return to backend directory for management commands
cd apps/backend

# See what was changed
python run.py --spec 001 --review

# Merge changes into your main branch
python run.py --spec 001 --merge

# Discard if you don't want the changes
python run.py --spec 001 --discard
```

---

## Interactive Controls

While the agent is running:

| Action | Keyboard | Description |
|--------|----------|-------------|
| Pause | `Ctrl+C` (once) | Pause and add instructions |
| Exit | `Ctrl+C` (twice) | Exit immediately |

### File-Based Alternative

For non-interactive control:

```bash
# Create PAUSE file to pause after current session
touch .magestic-ai/specs/001-name/PAUSE

# Add instructions for the agent
echo "Focus on fixing the login bug first" > .magestic-ai/specs/001-name/HUMAN_INPUT.md
```

---

## Spec Validation

Validate a spec before running:

```bash
python validate_spec.py --spec-dir .magestic-ai/specs/001-feature --checkpoint all
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `CLAUDE_CODE_OAUTH_TOKEN` | Yes | OAuth token from `claude setup-token` |
| `AUTO_BUILD_MODEL` | No | Model override (default: claude-opus-4-5-20251101) |
| `GRAPHITI_ENABLED` | No | Enable Graphiti memory system (default: true) |

---

## Directory Structure

Understanding the key directories for CLI operations:

```
project-root/
├── apps/
│   └── backend/           # Run CLI commands from here
│       ├── run.py         # Main build runner
│       ├── spec_runner.py # Spec creation
│       └── validate_spec.py # Spec validation
│
├── .magestic-ai/
│   ├── specs/             # Generated specifications
│   │   └── 001-feature/
│   │       ├── spec.md
│   │       ├── implementation_plan.json
│   │       └── build-progress.txt
│   │
│   └── worktrees/         # Isolated Git worktrees
│       └── tasks/
│           └── 001-feature/  # Task worktree
```

---

## Common CLI Workflows

### Quick Task Creation

```bash
cd apps/backend
source .venv/bin/activate
python spec_runner.py --task "Add dark mode toggle" --complexity simple
```

### Full Build Cycle

```bash
# Create spec
python spec_runner.py --task "Implement user profile page"

# Run build
python run.py --spec 002

# Review changes
python run.py --spec 002 --review

# Merge if satisfied
python run.py --spec 002 --merge
```

### Resuming Interrupted Work

```bash
# List specs to find the one you want
python run.py --list

# Continue the spec
python spec_runner.py --continue 003-interrupted-task
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Module not found" | Ensure virtual environment is activated: `source .venv/bin/activate` |
| "Token invalid" | Re-run `claude setup-token` and update `.env` |
| "Worktree exists" | Delete orphaned worktree: `git worktree remove .magestic-ai/worktrees/tasks/001-name` |
| "Spec not found" | Check spec exists in `.magestic-ai/specs/` directory |
| Python version error | Ensure Python 3.12+ is installed and in PATH |

---

## See Also

- [Getting Started](GETTING-STARTED.md) - Full installation guide
- [Configuration](CONFIGURATION.md) - All configuration options
- [Architecture](ARCHITECTURE.md) - System design overview
- [Web UI Guide](WEB-UI-GUIDE.md) - Using the browser interface

---

**MagesticAI** - CLI tools for power users
