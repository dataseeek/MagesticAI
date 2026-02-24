# Claude Code Manager Web - Web UI Guide

This guide provides a comprehensive walkthrough of the Claude Code Manager Web user interface. It covers all views, features, and workflows to help you get the most out of the platform.

---

## Table of Contents

1. [Interface Overview](#interface-overview)
2. [Sidebar Navigation](#sidebar-navigation)
3. [Project Tab Bar](#project-tab-bar)
4. [Kanban Board View](#kanban-board-view)
5. [Terminals View](#terminals-view)
6. [Editor View](#editor-view)
7. [Worktrees View](#worktrees-view)
8. [Roadmap View](#roadmap-view)
9. [Ideation View](#ideation-view)
10. [Context View](#context-view)
11. [Chat View (Insights)](#chat-view-insights)
12. [Changelog View](#changelog-view)
13. [Agent Tools View](#agent-tools-view)
14. [GitHub Issues View](#github-issues-view)
15. [GitLab Issues View](#gitlab-issues-view)
16. [Task Creation Wizard](#task-creation-wizard)
17. [Task Detail Modal](#task-detail-modal)
18. [Settings](#settings)
19. [Keyboard Shortcuts](#keyboard-shortcuts)
20. [Tips and Best Practices](#tips-and-best-practices)

---

## Interface Overview

Claude Code Manager Web features a modern, responsive interface designed for efficient AI-powered development workflows. The main interface consists of:

```
+------------------+----------------------------------------+
|                  |  Project Tab Bar                       |
|                  +----------------------------------------+
|                  |                                        |
|    Sidebar       |         Main Content Area              |
|   Navigation     |    (switches based on active view)     |
|                  |                                        |
|                  |                                        |
|                  |                                        |
|  +------------+  |                                        |
|  | Settings   |  |                                        |
|  | New Task   |  |                                        |
+------------------+----------------------------------------+
```

### Key Interface Elements

| Element | Location | Purpose |
|---------|----------|---------|
| **Sidebar** | Left side | View navigation, project selection, settings access |
| **Project Tab Bar** | Top | Switch between open projects, add new projects |
| **Main Content** | Center | Displays the active view (Kanban, Terminals, etc.) |
| **Task Detail Modal** | Overlay | Shows task details, logs, and actions |

---

## Sidebar Navigation

The sidebar provides access to all application views and key actions.

### Structure

1. **Header** - Application branding ("CC ManWeb")
2. **Project Selector** - Dropdown to select or add projects
3. **Navigation Items** - View switching buttons with keyboard shortcuts
4. **Footer** - Settings, help, and New Task button

### Navigation Items

| Icon | View | Shortcut | Description |
|------|------|----------|-------------|
| Grid | Kanban | `K` | Task board with drag-and-drop management |
| Terminal | Terminals | `A` | Multi-terminal grid with Claude integration |
| Code | Editor | `E` | Monaco code editor with file browser |
| Sparkles | Chat | `N` | AI-powered codebase Q&A |
| Map | Roadmap | `D` | AI-generated feature roadmap |
| Lightbulb | Ideation | `I` | AI-powered feature brainstorming |
| FileText | Changelog | `L` | Automatic changelog generation |
| Book | Context | `C` | Project indexing and memory management |
| Wrench | Agent Tools | `M` | MCP tools configuration |
| Branch | Worktrees | `W` | Git worktree management |

### Conditional Navigation

When GitHub or GitLab integrations are enabled:

| Icon | View | Shortcut | Description |
|------|------|----------|-------------|
| GitHub | GitHub Issues | `G` | GitHub issue tracking integration |
| Pull Request | GitHub PRs | `P` | Pull request management |
| GitLab | GitLab Issues | `B` | GitLab issue tracking |
| Merge | GitLab MRs | `R` | Merge request management |

### Footer Actions

- **Claude Code Status Badge** - Shows Claude Code CLI status
- **Rate Limit Indicator** - Displays API rate limiting status
- **Settings Button** - Opens application settings dialog
- **Help Button** - Access documentation and support
- **New Task Button** - Creates a new AI task (requires initialized project)

---

## Project Tab Bar

The project tab bar allows you to work with multiple projects simultaneously.

### Features

- **Tab switching** - Click tabs to switch between open projects
- **Drag reordering** - Drag tabs to reorder them
- **Close tabs** - Click the X on a tab to close that project
- **Add project** - Click the + button to add a new project
- **Settings access** - Quick access to settings

### Tab Indicators

- **Active tab** - Highlighted with primary color
- **Modified** - May show indicators for unsaved changes
- **Project name** - Displays project name or directory name

---

## Kanban Board View

The Kanban board is the primary task management interface, providing visual workflow tracking.

### Columns

| Column | Status | Description |
|--------|--------|-------------|
| **Backlog** | `backlog` | Tasks waiting to start |
| **In Progress** | `in_progress` | AI agents actively working |
| **AI Review** | `ai_review` | QA agent reviewing implementation |
| **Human Review** | `human_review` | Ready for your review |
| **Done** | `done` | Completed and merged |

### Features

#### Task Cards
Each task card displays:
- Task title
- Status indicator with color coding
- Execution progress (phase, percentage)
- Updated timestamp

#### Drag and Drop
- Drag cards between columns to change status
- Visual feedback shows valid drop zones
- Status changes are persisted immediately

#### Column Actions
- **Backlog** - "+" button to create new tasks
- **Done** - Archive button to hide completed tasks
- **Archive toggle** - Show/hide archived tasks

### Color Coding

| Column | Border Color |
|--------|-------------|
| Backlog | Gray |
| In Progress | Orange |
| AI Review | Violet |
| Human Review | Fuchsia |
| Done | Emerald |

### Empty States

Each column shows helpful messages when empty:
- **Backlog**: "No tasks in backlog. Create a new task to get started."
- **In Progress**: "No tasks currently running."
- **Done**: "No completed tasks yet."

---

## Terminals View

The Terminals view provides a multi-terminal grid for running commands and Claude agents.

### Features

#### Terminal Grid
- **Resizable panels** - Drag separators to resize terminals
- **Dynamic layout** - Grid adjusts based on terminal count (1-12 terminals)
- **Active terminal indicator** - Highlighted border on focused terminal

#### Terminal Header
Each terminal has a header with:
- **Title** - Customizable terminal name
- **Worktree selector** - Switch to task worktrees
- **Task selector** - Associate terminal with a task
- **Close button** - Close the terminal

#### Claude Integration
- **Claude Mode** - Type "claude" to enter Claude CLI
- **Open Claude All** - Button to start Claude in all terminals
- **Visual indicator** - Shows when terminal is in Claude mode

#### Session History
- **History dropdown** - View past terminal sessions by date
- **Restore sessions** - Restore terminal layout from previous sessions
- **Session persistence** - Sessions are saved and can be restored

#### File Explorer Panel
- **Toggle button** - "Files" button in toolbar
- **Drag and drop** - Drag files into terminals to insert paths
- **Path quoting** - Paths with spaces are automatically quoted

### Toolbar Actions

| Button | Description |
|--------|-------------|
| **History** | Restore sessions from previous dates |
| **Open Claude All** | Start Claude CLI in all running terminals |
| **New Terminal** | Create a new terminal (max 12) |
| **Files** | Toggle file explorer panel |

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+Shift+E` / `Cmd+Shift+E` | New terminal |
| `Ctrl+W` / `Cmd+W` | Close active terminal |

---

## Editor View

The Editor view provides a VS Code-like editing experience using Monaco Editor.

### Features

#### File Explorer
- **Tree navigation** - Lazy-loaded directory tree
- **Folder icons** - Blue folder icons for directories
- **File icons** - Gray file icons for files
- **Click to open** - Click files to open in editor

#### Tab Bar
- **Multiple tabs** - Open multiple files simultaneously
- **Dirty indicator** - Asterisk (*) shows unsaved changes
- **Close button** - X button to close tabs
- **Active tab** - Highlighted background

#### Monaco Editor
- **Syntax highlighting** - 40+ languages supported
- **Minimap** - Code overview on the right
- **Line numbers** - Line number gutter
- **Word wrap** - Configurable text wrapping

#### Status Bar
- **File path** - Shows current file location
- **Language** - Detected file language
- **Save button** - Save current file

### Supported Languages

TypeScript, JavaScript, Python, Ruby, Rust, Go, Java, C/C++, C#, PHP, Swift, Kotlin, Scala, R, SQL, HTML, CSS, SCSS, JSON, YAML, XML, Markdown, Shell, Docker, and more.

---

## Worktrees View

The Worktrees view manages Git worktrees created for each task.

### What are Worktrees?

Git worktrees are isolated working directories that share the same Git repository. Claude Code Manager Web creates a worktree for each task, providing:
- **Isolation** - Each task has its own workspace
- **Clean merges** - Changes don't conflict between tasks
- **Easy review** - Review each task's changes separately

### Worktree Cards

Each worktree card displays:
- **Branch name** - The task's feature branch
- **Task title** - Associated task description
- **Spec ID** - Task identifier badge
- **Statistics**:
  - Files changed
  - Commits ahead of base
  - Lines added (+) and removed (-)
- **Branch flow** - Base branch → Feature branch

### Actions

| Action | Description |
|--------|-------------|
| **Merge to base** | Merge worktree changes to base branch |
| **Copy Path** | Copy worktree directory path to clipboard |
| **Delete** | Remove worktree and discard changes |

### Cleanup

- **Cleanup Empty** - Button to remove worktrees with no changes
- **Empty count** - Shows number of empty worktrees

### Merge Dialog

When merging:
1. Shows source and target branches
2. Displays change summary (commits, files)
3. Confirms merge operation
4. Shows success/failure result with conflict details if any

---

## Roadmap View

The Roadmap view displays an AI-generated feature roadmap for your project.

### Generation

1. Click **"Generate Roadmap"** on empty state
2. Optionally include **Competitor Analysis** for market context
3. AI analyzes your codebase and generates phased roadmap

### Phases

Features are organized into development phases:
- **Phase 1**: Foundation/Core features
- **Phase 2**: Enhancement features
- **Phase 3**: Advanced features
- **Future**: Long-term vision

### View Modes

| Tab | Description |
|-----|-------------|
| **Kanban** | Features organized by phase columns |
| **Timeline** | Chronological feature timeline |
| **List** | Compact list view of all features |

### Feature Cards

Each feature displays:
- Feature name and description
- Priority indicator
- Complexity estimate
- Status (planned, in-progress, done)
- Associated task link (if converted)

### Actions

| Action | Description |
|--------|-------------|
| **Add Feature** | Manually add a feature to the roadmap |
| **Refresh** | Re-generate roadmap with current codebase |
| **View Competitor Analysis** | View market analysis results |
| **Convert to Spec** | Create task from feature |
| **Go to Task** | Navigate to associated task |

### Feature Detail Panel

Click a feature to see:
- Full description
- Acceptance criteria
- Competitor insights (if available)
- Conversion options

---

## Ideation View

The Ideation view generates AI-powered feature ideas for your project.

### Idea Types

| Type | Description |
|------|-------------|
| **Feature** | New functionality to add |
| **Enhancement** | Improvements to existing features |
| **Bug Fix** | Potential issues to address |
| **Optimization** | Performance improvements |
| **Security** | Security enhancements |
| **UX** | User experience improvements |

### Generation Process

1. Configure which idea types to generate
2. Click **"Generate Ideas"**
3. Watch ideas stream in real-time
4. Review and act on generated ideas

### Idea Cards

Each idea shows:
- Idea title and description
- Type badge (color-coded)
- Priority indicator
- Status (active, dismissed, converted)

### Actions

| Action | Description |
|--------|-------------|
| **Convert to Task** | Create spec from idea |
| **Go to Task** | Navigate to converted task |
| **Dismiss** | Hide idea from active list |
| **Multi-select** | Select multiple ideas for bulk actions |

### Filters

- **Type tabs** - Filter by idea type
- **Show Dismissed** - Toggle dismissed ideas visibility
- **Show Archived** - Toggle archived ideas

### Idea Detail Panel

Click an idea to see:
- Full description
- Implementation suggestions
- Related code areas
- Action buttons

---

## Context View

The Context view manages project indexing and AI memory.

### Tabs

#### Project Index Tab

Shows the indexed structure of your codebase:
- **File tree** - Project structure
- **Index statistics** - File counts, types
- **Refresh button** - Re-index project

Benefits of indexing:
- Faster AI responses
- Better context understanding
- More accurate code suggestions

#### Memories Tab

Graphiti-powered knowledge graph for cross-session learning:

**Memory Status**:
- **Enabled/Disabled** - Whether Graphiti is active
- **Memory count** - Number of stored memories
- **Last updated** - When memories were last modified

**Search**:
- Semantic search through memories
- Filter by category
- View memory details

**Memory Types**:
- Session insights
- Code patterns
- Architectural decisions
- Bug fixes

---

## Chat View (Insights)

The Chat view provides an AI-powered Q&A interface for your codebase.

### Features

#### Conversation Interface
- **Chat messages** - User and assistant message bubbles
- **Markdown rendering** - Rich text formatting
- **Code blocks** - Syntax-highlighted code snippets
- **Streaming responses** - Real-time response streaming

#### Tool Usage
During responses, the AI may use tools:
- **Read** - Reading file contents
- **Glob** - Searching for files
- **Grep** - Searching code content

Tool usage is displayed with:
- Real-time indicator during execution
- Collapsed summary after completion
- Expandable tool history

#### Task Suggestions
The AI can suggest tasks based on discussion:
- **Suggested Task card** - Title and description
- **Category badge** - Task type indicator
- **Complexity badge** - Effort estimate
- **Create Task button** - One-click task creation

### Chat History Sidebar

- **Session list** - Past conversations
- **New Chat** - Start fresh conversation
- **Rename** - Rename conversation sessions
- **Delete** - Remove old sessions

### Model Selection

- **Model dropdown** - Choose Claude model
- **Configuration** - Adjust model parameters

### Suggested Prompts

Empty state shows starter prompts:
- "What is the architecture of this project?"
- "Suggest improvements for code quality"
- "What features could I add next?"
- "Are there any security concerns?"

---

## Changelog View

The Changelog view generates release notes from your Git history.

### Features

- **Automatic generation** - Parses commits and pull requests
- **Categorized changes** - Groups by type (features, fixes, etc.)
- **Version tracking** - Organizes by version/tag
- **Export options** - Export as Markdown

### Categories

| Category | Description |
|----------|-------------|
| **Features** | New functionality |
| **Bug Fixes** | Issue resolutions |
| **Improvements** | Enhancements |
| **Breaking Changes** | API changes |
| **Documentation** | Doc updates |

---

## Agent Tools View

The Agent Tools view manages MCP (Model Context Protocol) tools available to AI agents.

### Features

- **Tool list** - Available MCP tools
- **Configuration** - Tool settings
- **Custom tools** - Add custom MCP servers

### Tool Categories

- File operations
- Search tools
- Git operations
- Custom integrations

---

## GitHub Issues View

Integrates with GitHub for issue management.

### Prerequisites

- GitHub token configured in project `.env`
- Repository connected

### Features

- **Issue list** - View repository issues
- **Create issue** - Open new issues
- **Convert to task** - Create spec from issue
- **Status sync** - Issue status updates

### Filters

- Open/Closed
- Labels
- Assignee
- Milestone

---

## GitLab Issues View

Integrates with GitLab for issue management.

### Prerequisites

- GitLab token configured in project `.env`
- Project connected

### Features

- **Issue list** - View project issues
- **Create issue** - Open new issues
- **Convert to task** - Create spec from issue
- **Labels** - Issue categorization

---

## Task Creation Wizard

The Task Creation Wizard guides you through creating AI-powered tasks.

### Steps

1. **Description** - Enter what you want to build
2. **Spec Generation** - AI generates specification
3. **Review** - Review and edit the spec
4. **Confirm** - Create the task

### Description Tips

**Good descriptions:**
- "Add a dark mode toggle to settings with system preference detection"
- "Create user registration form with email validation"
- "Fix login button disabled after failed attempt"

**Less effective:**
- "Make it better" (too vague)
- "Add everything" (no clear scope)

### Spec Contents

Generated spec includes:
- **Summary** - What will be implemented
- **Acceptance Criteria** - Success measurements
- **Complexity** - Estimated effort
- **Notes** - Additional context

### Options

- **Edit** - Modify generated spec
- **Regenerate** - Generate new spec
- **Cancel** - Discard and close

---

## Task Detail Modal

The Task Detail Modal provides comprehensive task information and controls.

### Sections

#### Header
- Task title
- Status badge
- Close button

#### Tabs

| Tab | Content |
|-----|---------|
| **Details** | Task specification and metadata |
| **Progress** | Execution phases and progress |
| **Logs** | Real-time agent logs |
| **Files** | Changed files with diff viewer |
| **Review** | Merge preview and QA feedback |

### Actions

| Action | When Available |
|--------|----------------|
| **Start Task** | Backlog status |
| **Stop** | In Progress |
| **Resume** | Paused |
| **Request Changes** | Human Review |
| **Merge** | Human Review |
| **Archive** | Done status |
| **Delete** | Any status |

### Execution Progress

Shows phase progression:
```
Discovery → Planning → Coding → QA Review → Done
```

Each phase displays:
- Phase name
- Progress percentage
- Current subtask (if applicable)

### Log Viewer

- Real-time streaming logs
- Color-coded log levels
- Timestamp display
- Auto-scroll option
- Search/filter logs

### Diff Viewer

- File-by-file changes
- Side-by-side diff
- Syntax highlighting
- Line additions/deletions

### Merge Preview

- Conflict detection
- File change summary
- Merge confirmation
- Post-merge cleanup options

---

## Settings

Access settings via the sidebar Settings button.

### Categories

#### General
- **Theme** - Light, Dark, System
- **Color Theme** - Accent color variants
- **UI Scale** - Interface sizing
- **Language** - Interface language

#### Projects
- **Default project path** - Where to look for projects
- **Auto Claude path** - Framework source path

#### Claude
- **Default model** - Claude model selection
- **Extended thinking** - Enable for complex tasks

#### Integrations
- **GitHub** - Token and repository settings
- **GitLab** - Token and project settings
- **Linear** - Issue tracking integration

#### Advanced
- **Debug mode** - Enable verbose logging
- **Developer options** - Advanced configuration

---

## Keyboard Shortcuts

### Global Shortcuts

| Shortcut | Action |
|----------|--------|
| `N` | New task (from Kanban) |
| `T` | New terminal |
| `Esc` | Close modals |
| `Ctrl+K` / `Cmd+K` | Command palette |

### View Navigation

| Shortcut | View |
|----------|------|
| `K` | Kanban |
| `A` | Terminals |
| `E` | Editor |
| `N` | Chat |
| `D` | Roadmap |
| `I` | Ideation |
| `L` | Changelog |
| `C` | Context |
| `M` | Agent Tools |
| `W` | Worktrees |

### Terminal Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+Shift+E` / `Cmd+Shift+E` | New terminal |
| `Ctrl+W` / `Cmd+W` | Close active terminal |

### Chat Shortcuts

| Shortcut | Action |
|----------|--------|
| `Enter` | Send message |
| `Shift+Enter` | New line |

---

## Tips and Best Practices

### Task Management

1. **Clear descriptions** - Be specific about what you want
2. **Review specs** - Always review generated specs before starting
3. **Monitor progress** - Watch logs for issues early
4. **Iterate** - Use QA feedback to improve

### Terminal Usage

1. **Multiple terminals** - Use parallel terminals for different tasks
2. **Session persistence** - Sessions are saved automatically
3. **Claude mode** - Use "Open Claude All" for multi-agent work
4. **File drag-drop** - Drag files to insert paths

### Worktree Workflow

1. **One task, one worktree** - Keep changes isolated
2. **Regular merges** - Merge completed tasks promptly
3. **Cleanup** - Remove empty worktrees regularly
4. **Review before merge** - Check diff before merging

### Memory System

1. **Enable Graphiti** - Set `GRAPHITI_ENABLED=true` for learning
2. **Index project** - Keep project index updated
3. **Search memories** - Use semantic search for past insights

### Performance

1. **Close unused tabs** - Free memory by closing projects
2. **Limit terminals** - Don't exceed needed terminal count
3. **Archive done tasks** - Keep Kanban board clean

### Troubleshooting

1. **Refresh** - Try refreshing the page for UI issues
2. **Check logs** - View agent logs for task issues
3. **Verify token** - Ensure Claude token is valid
4. **Check backend** - Verify web-server is running

---

## Related Guides

- **[Getting Started](GETTING-STARTED.md)** - Installation and first task
- **[Task Workflow](TASK-WORKFLOW.md)** - Understanding the task lifecycle
- **[CLI Usage](CLI-USAGE.md)** - Terminal-based operations
- **[Configuration](CONFIGURATION.md)** - Environment and settings
- **[Troubleshooting](TROUBLESHOOTING.md)** - Common issues and solutions

---

**Claude Code Manager Web** - Master your AI-powered development workflow!
