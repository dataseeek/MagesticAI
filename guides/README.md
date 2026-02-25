# MagesticAI - Documentation

Welcome to the **MagesticAI** documentation! This guides section provides comprehensive documentation for users, developers, and contributors working with our web-based AI task management platform.

## What is MagesticAI?

MagesticAI is a **browser-based platform** for managing AI-powered coding tasks through coordinated autonomous agents. It provides a modern web interface for:

- **Task Creation & Management** - Create and track coding tasks through an intuitive Kanban board
- **AI Agent Orchestration** - Coordinate Planner, Coder, and QA agents to implement features
- **Real-time Terminal Access** - Full PTY terminal access directly in your browser
- **Code Editing** - VS Code-like editing experience with Monaco Editor
- **Git Worktree Isolation** - Safe, isolated branches per task with easy merge workflows

Access the application from any modern browser - no desktop installation required!

---

## Guide Overview

### Getting Started

| Guide | Description | Audience |
|-------|-------------|----------|
| [Getting Started](GETTING-STARTED.md) | Installation, first run, and your first task | New Users |
| [Web UI Guide](WEB-UI-GUIDE.md) | Complete walkthrough of all views and features | All Users |
| [Task Workflow](TASK-WORKFLOW.md) | Understanding the task lifecycle (Create → Plan → Code → QA → Merge) | All Users |

### Using the Application

| Guide | Description | Audience |
|-------|-------------|----------|
| [CLI Usage](CLI-USAGE.md) | Terminal-based operations and power user workflows | Power Users |
| [Configuration](CONFIGURATION.md) | Environment variables, settings, and customization | All Users |
| [Troubleshooting](TROUBLESHOOTING.md) | Common issues, solutions, and debugging tips | All Users |

### Development & Contributing

| Guide | Description | Audience |
|-------|-------------|----------|
| [Development Setup](DEVELOPMENT-SETUP.md) | Setting up the development environment | Developers |
| [Architecture](ARCHITECTURE.md) | System design, data flow, and component interactions | Developers |
| [API Reference](API-REFERENCE.md) | REST endpoints and WebSocket events documentation | Developers |

---

## Quick Links

| Resource | Description |
|----------|-------------|
| [Main README](../README.md) | Project overview, quick start, and tech stack |
| [Technical Docs](../DOCS.md) | In-depth technical documentation |
| [Contributing Guide](../CONTRIBUTING.md) | How to contribute to the project |
| [Changelog](../CHANGELOG.md) | Release history and version notes |
| [License](../LICENSE) | AGPL-3.0 license details |

---

## Application Views at a Glance

MagesticAI provides multiple specialized views accessible from the sidebar:

| View | Purpose |
|------|---------|
| **Kanban** | Task board with drag-and-drop status management |
| **Terminals** | Multi-terminal grid with full PTY support |
| **Editor** | Monaco code editor with integrated file browser |
| **Worktrees** | Git worktree management and merge operations |
| **Roadmap** | AI-generated feature roadmap visualization |
| **Ideation** | AI-powered feature brainstorming |
| **Context** | Project indexing and memory management |
| **GitHub/GitLab Issues** | Issue tracker integrations |
| **GitHub PRs** | Pull request AI review workflow |
| **Changelog** | Automatic changelog generation |
| **Insights** | AI analysis and project health metrics |

---

## Getting Help

- **Issues:** [GitHub Issues](https://github.com/dataseeek/Claude-Code-Manager-Web/issues)
- **Discussions:** [GitHub Discussions](https://github.com/dataseeek/Claude-Code-Manager-Web/discussions)
- **Troubleshooting:** See [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

---

## Prerequisites Summary

Before using MagesticAI, ensure you have:

- **Node.js 24+** with npm 10+
- **Python 3.12+**
- **Git** (for repository operations)
- **Claude Code OAuth Token** (run `claude setup-token` to obtain)
- **A modern web browser** (Chrome, Firefox, Safari, or Edge)

For detailed installation instructions, see [Getting Started](GETTING-STARTED.md).

---

**MagesticAI** - Orchestrate AI coding agents from your browser.
