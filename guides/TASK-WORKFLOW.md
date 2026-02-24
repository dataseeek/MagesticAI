# Claude Code Manager Web - Task Workflow Guide

This guide explains the complete task lifecycle in Claude Code Manager Web, from initial creation through final merge. Understanding this workflow helps you get the most out of AI-powered development.

---

## Table of Contents

1. [Overview](#overview)
2. [Task Lifecycle Phases](#task-lifecycle-phases)
3. [Phase 1: Task Creation](#phase-1-task-creation)
4. [Phase 2: Planning](#phase-2-planning)
5. [Phase 3: Coding](#phase-3-coding)
6. [Phase 4: QA Review](#phase-4-qa-review)
7. [Phase 5: Human Review](#phase-5-human-review)
8. [Phase 6: Merge](#phase-6-merge)
9. [Agent Roles Explained](#agent-roles-explained)
10. [Monitoring Progress](#monitoring-progress)
11. [Intervening and Guiding Agents](#intervening-and-guiding-agents)
12. [Troubleshooting Common Issues](#troubleshooting-common-issues)
13. [Best Practices](#best-practices)

---

## Overview

Claude Code Manager Web uses a multi-agent orchestration system to implement features autonomously. Each task progresses through a series of phases, with specialized AI agents handling different aspects of the work.

### The Big Picture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        TASK LIFECYCLE                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐      │
│  │          │    │          │    │          │    │          │      │
│  │ CREATE   │───▶│ PLANNING │───▶│ CODING   │───▶│   QA     │      │
│  │          │    │          │    │          │    │ REVIEW   │      │
│  └──────────┘    └──────────┘    └──────────┘    └────┬─────┘      │
│       │                                               │            │
│       │              Spec                Planner     QA Reviewer   │
│       │              Writer              Agent       Agent         │
│       │                │                   │           │           │
│       ▼                │                   │           ▼           │
│  User writes    Analyzes codebase    Coder Agent  ┌──────────┐     │
│  description    Creates subtasks     implements   │ ISSUES?  │     │
│                                      each task    └────┬─────┘     │
│                                                        │           │
│                                          ┌─────────────┴──────┐    │
│                                          │                    │    │
│                                          ▼                    ▼    │
│                                    ┌──────────┐        ┌──────────┐│
│                                    │ QA FIXER │        │  HUMAN   ││
│                                    │ (auto)   │        │  REVIEW  ││
│                                    └──────────┘        └────┬─────┘│
│                                          │                  │      │
│                                          │                  ▼      │
│                                          │           ┌──────────┐  │
│                                          └──────────▶│  MERGE   │  │
│                                                      │          │  │
│                                                      └──────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Key Concepts

| Concept | Description |
|---------|-------------|
| **Spec** | A specification document describing what to build |
| **Implementation Plan** | A breakdown of subtasks to complete the spec |
| **Worktree** | An isolated Git workspace for the task |
| **Agent** | An AI process that performs specific work (planning, coding, QA) |
| **Subtask** | A single unit of work within the implementation plan |

---

## Task Lifecycle Phases

Every task moves through these phases on the Kanban board:

| Phase | Kanban Column | Description | Agent(s) Involved |
|-------|---------------|-------------|-------------------|
| **Create** | Backlog | Spec creation and task setup | Spec Writer |
| **Planning** | In Progress | Implementation plan generation | Planner Agent |
| **Coding** | In Progress | Subtask implementation | Coder Agent |
| **QA Review** | AI Review | Automated code review | QA Reviewer, QA Fixer |
| **Human Review** | Human Review | Manual review and approval | You! |
| **Merge** | Done | Code merged to base branch | Manual action |

### Phase Duration

| Phase | Typical Duration | Factors Affecting Duration |
|-------|-----------------|---------------------------|
| Create | 1-3 minutes | Spec complexity, codebase size |
| Planning | 2-5 minutes | Number of subtasks needed |
| Coding | 5-60 minutes | Task complexity, subtask count |
| QA Review | 2-10 minutes | Issues found, iterations needed |
| Human Review | Variable | Your availability, review depth |
| Merge | < 1 minute | Conflict resolution if needed |

---

## Phase 1: Task Creation

### What Happens

When you create a new task, the system:

1. **Captures your request** - You describe what you want to build
2. **Analyzes the codebase** - AI scans relevant files and patterns
3. **Generates a specification** - Creates a detailed spec.md file
4. **Creates a worktree** - Sets up an isolated Git branch for the task

### How to Create a Task

#### Using the Task Creation Wizard

1. Click **"+ New Task"** from the Kanban board (or press `N`)
2. Enter a clear description of what you want
3. Wait for spec generation (usually 30-60 seconds)
4. Review the generated specification
5. Edit, regenerate, or accept the spec
6. Confirm to create the task

#### Writing Effective Descriptions

**Do:**
```
Add a dark mode toggle to the settings page that:
- Persists user preference to localStorage
- Respects system preference by default
- Uses smooth transitions between themes
- Updates the header, sidebar, and main content areas
```

**Don't:**
```
Make the app look better
```

### Generated Spec Structure

Each spec includes:

```markdown
# Task Title

## Summary
What will be implemented and why.

## Acceptance Criteria
- [ ] Specific, testable requirements
- [ ] Each criterion is verifiable
- [ ] Clear success conditions

## Notes
Additional context, constraints, or considerations.
```

### Files Created

| File | Location | Purpose |
|------|----------|---------|
| `spec.md` | `.auto-claude/specs/{task-id}/` | Feature specification |
| `requirements.json` | `.auto-claude/specs/{task-id}/` | User requirements |
| `context.json` | `.auto-claude/specs/{task-id}/` | Codebase context |
| Worktree | `.auto-claude/worktrees/tasks/{task-id}/` | Isolated workspace |

---

## Phase 2: Planning

### What Happens

The **Planner Agent** analyzes your spec and codebase to create a detailed implementation plan.

1. **Reads the specification** - Understands what needs to be built
2. **Explores the codebase** - Identifies relevant files and patterns
3. **Designs the approach** - Determines how to implement the feature
4. **Creates subtasks** - Breaks work into manageable pieces
5. **Saves the plan** - Writes `implementation_plan.json`

### Implementation Plan Structure

```json
{
  "task_id": "001-dark-mode",
  "title": "Add Dark Mode Toggle",
  "status": "in_progress",
  "phases": [
    {
      "id": "phase-1",
      "name": "Theme Infrastructure",
      "subtasks": [
        {
          "id": "1.1",
          "title": "Create theme context",
          "description": "Add React context for theme state management",
          "status": "pending",
          "estimated_effort": "small",
          "dependencies": [],
          "acceptance_criteria": [
            "Context provides current theme",
            "Includes toggle function"
          ]
        }
      ]
    }
  ]
}
```

### Subtask Properties

| Property | Description |
|----------|-------------|
| `id` | Unique identifier (e.g., "1.1", "2.3") |
| `title` | Short description of what to do |
| `description` | Detailed explanation |
| `status` | pending, in_progress, completed |
| `estimated_effort` | small, medium, large |
| `dependencies` | IDs of subtasks that must complete first |
| `acceptance_criteria` | How to verify completion |

### Plan Quality

Good plans have:
- **Clear phases** - Logical groupings of related work
- **Appropriate granularity** - Not too big, not too small
- **Proper dependencies** - Tasks ordered correctly
- **Testable criteria** - Each subtask has verification steps

---

## Phase 3: Coding

### What Happens

The **Coder Agent** implements each subtask sequentially:

1. **Loads the subtask** - Reads requirements and context
2. **Explores relevant code** - Finds files to modify
3. **Makes changes** - Implements the feature
4. **Commits progress** - Creates Git commits
5. **Updates status** - Marks subtask complete
6. **Moves to next** - Proceeds to the next subtask

### Execution Flow

```
Subtask 1.1 ──▶ Subtask 1.2 ──▶ Subtask 2.1 ──▶ Subtask 2.2
    │              │              │              │
    ▼              ▼              ▼              ▼
 Commit 1       Commit 2       Commit 3       Commit 4
```

### Subtask Status Progression

```
pending → in_progress → completed
                │
                └──▶ (on failure) ──▶ blocked
```

### What the Coder Agent Does

- Reads and writes files
- Runs commands (npm install, pytest, etc.)
- Creates directories
- Uses Git for version control
- Follows existing code patterns
- Respects project conventions

### What the Coder Agent Cannot Do

- Run destructive system commands
- Access files outside the project
- Make network requests to unknown hosts
- Push code to remote repositories
- Delete important configuration files

---

## Phase 4: QA Review

### What Happens

After coding completes, the **QA Reviewer Agent** validates the implementation:

1. **Reviews all changes** - Reads the diff against base branch
2. **Checks acceptance criteria** - Verifies each requirement
3. **Runs tests** - Executes project test suite
4. **Identifies issues** - Documents problems found
5. **Decides outcome** - Approves or requests fixes

### QA Outcomes

| Outcome | What Happens Next |
|---------|-------------------|
| **Approved** | Task moves to Human Review |
| **Issues Found** | QA Fixer Agent attempts repairs |
| **Critical Issues** | Task escalates to Human Review |

### QA Review Process

```
┌──────────────────────────────────────────────────────────┐
│                     QA REVIEW LOOP                        │
├──────────────────────────────────────────────────────────┤
│                                                          │
│    ┌───────────┐                                         │
│    │ QA Review │                                         │
│    └─────┬─────┘                                         │
│          │                                               │
│          ▼                                               │
│    ┌───────────┐         ┌───────────┐                  │
│    │  PASS?    │── No ──▶│ QA Fixer  │                  │
│    └─────┬─────┘         └─────┬─────┘                  │
│          │                     │                         │
│          │                     │                         │
│        Yes                     └──────────┐              │
│          │                                │              │
│          ▼                                │              │
│    ┌───────────┐                          │              │
│    │  Human    │◀───── (max 10 loops) ────┘              │
│    │  Review   │                                         │
│    └───────────┘                                         │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### QA Report

The QA process generates a report:

```markdown
# QA Report

## Summary
Overall assessment of the implementation.

## Tests Run
- Unit tests: 45/45 passed
- Integration tests: 12/12 passed
- Type checking: No errors

## Issues Found
None

## Recommendation
APPROVED - Ready for human review.
```

### QA Fix Requests

When issues are found:

```markdown
# QA Fix Request

## Issue 1: Missing error handling
**Severity:** Medium
**File:** src/components/DarkModeToggle.tsx
**Description:** The toggle doesn't handle localStorage errors gracefully.
**Suggested Fix:** Add try-catch block around localStorage operations.

## Issue 2: Test coverage
**Severity:** Low
**File:** src/components/DarkModeToggle.test.tsx
**Description:** Missing test for system preference detection.
```

---

## Phase 5: Human Review

### What Happens

After passing AI review, the task awaits your approval:

1. **Review the changes** - Examine code diffs
2. **Test functionality** - Verify in the worktree
3. **Make a decision** - Approve, request changes, or reject

### Review Checklist

Before approving, verify:

- [ ] Changes match the original spec
- [ ] Code quality meets project standards
- [ ] Tests pass and cover new code
- [ ] No unintended side effects
- [ ] Documentation updated if needed

### How to Review

#### In the Web UI

1. Click the task card to open the Task Detail Modal
2. Navigate to the **Files** tab to see changes
3. Use the diff viewer to examine each file
4. Check the **Progress** tab for subtask completion
5. Review the **Logs** tab for agent activity

#### In the Worktree

```bash
# Navigate to the task worktree
cd .auto-claude/worktrees/tasks/001-dark-mode/

# View the changes
git diff main

# Run tests
npm test

# Start the dev server
npm run dev
```

### Review Actions

| Action | When to Use | Effect |
|--------|-------------|--------|
| **Merge** | Implementation is correct | Merges to base branch |
| **Request Changes** | Minor fixes needed | Returns to QA phase |
| **Reject** | Major issues, start over | Task moves to failed |

### Providing Feedback

When requesting changes, be specific:

**Good feedback:**
```
The toggle works but needs:
1. Add aria-label for accessibility
2. Move the toggle to the left side of the header
3. Use the existing animation utilities instead of custom CSS
```

**Less helpful feedback:**
```
This doesn't look right, please fix
```

---

## Phase 6: Merge

### What Happens

When you approve a task:

1. **Merge confirmation** - You confirm the merge action
2. **Git merge** - Changes merge to your base branch
3. **Worktree cleanup** - Option to delete the worktree
4. **Task completed** - Moves to Done column

### Merge Options

| Option | Description |
|--------|-------------|
| **Merge and Keep Worktree** | Merges but keeps worktree for reference |
| **Merge and Delete Worktree** | Merges and removes the worktree |
| **Cancel** | Abort the merge |

### Handling Conflicts

If conflicts arise during merge:

1. The system will notify you of conflicts
2. Navigate to the worktree directory
3. Resolve conflicts manually:
   ```bash
   cd .auto-claude/worktrees/tasks/001-dark-mode/
   git status
   # Edit conflicted files
   git add .
   git commit -m "Resolve merge conflicts"
   ```
4. Retry the merge from the UI

### Post-Merge

After a successful merge:

- Your main branch includes the new feature
- The task moves to the **Done** column
- You can archive the task to hide it
- The worktree can be deleted to free disk space

---

## Agent Roles Explained

### Spec Writer Agent

**Purpose:** Creates feature specifications from user descriptions.

| Capability | Description |
|------------|-------------|
| Codebase analysis | Scans project structure and patterns |
| Requirements gathering | Translates descriptions to requirements |
| Context awareness | Understands existing architecture |
| Spec generation | Creates detailed spec.md files |

**Tools Used:**
- File reading (Glob, Read, Grep)
- Codebase exploration

### Planner Agent

**Purpose:** Creates implementation plans with subtasks.

| Capability | Description |
|------------|-------------|
| Architecture analysis | Understands system design |
| Task decomposition | Breaks work into subtasks |
| Dependency mapping | Orders tasks correctly |
| Effort estimation | Predicts complexity |

**Tools Used:**
- File reading
- Implementation plan writing

### Coder Agent

**Purpose:** Implements subtasks by writing code.

| Capability | Description |
|------------|-------------|
| Code writing | Creates and modifies files |
| Command execution | Runs build/test commands |
| Pattern following | Matches existing code style |
| Git operations | Commits changes |

**Tools Used:**
- File read/write
- Bash commands
- Git operations
- MCP tools (if configured)

### QA Reviewer Agent

**Purpose:** Validates implementations against specifications.

| Capability | Description |
|------------|-------------|
| Code review | Examines changes for issues |
| Test execution | Runs project test suite |
| Criteria validation | Checks acceptance criteria |
| Issue documentation | Records problems found |

**Tools Used:**
- File reading
- Test command execution
- Report generation

### QA Fixer Agent

**Purpose:** Resolves issues found during QA review.

| Capability | Description |
|------------|-------------|
| Issue resolution | Fixes documented problems |
| Code modification | Updates implementation |
| Test fixing | Resolves failing tests |

**Tools Used:**
- Same as Coder Agent

---

## Monitoring Progress

### Kanban Board

The Kanban board provides a high-level view of all tasks:

```
┌─────────────┬─────────────┬─────────────┬─────────────┬─────────────┐
│   Backlog   │ In Progress │  AI Review  │Human Review │    Done     │
├─────────────┼─────────────┼─────────────┼─────────────┼─────────────┤
│             │             │             │             │             │
│  Task A     │  Task B     │  Task C     │  Task D     │  Task E     │
│  (pending)  │  (coding)   │  (qa)       │  (review)   │  (merged)   │
│             │             │             │             │             │
└─────────────┴─────────────┴─────────────┴─────────────┴─────────────┘
```

### Task Detail Modal

Click any task card to see detailed information:

#### Progress Tab

Shows phase progression and current activity:

```
Discovery     ████████████████████████████████  100%
Planning      ████████████████████████████████  100%
Coding        ████████████████████░░░░░░░░░░░░   65%
  └─ Subtask 2.3: Adding theme context  [in progress]
QA Review     ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░    0%
```

#### Logs Tab

Real-time agent activity:

```
[14:32:15] Starting subtask 2.3: Adding theme context
[14:32:17] Reading file: src/contexts/ThemeContext.tsx
[14:32:19] Creating new file: src/hooks/useTheme.ts
[14:32:22] Running command: npm run typecheck
[14:32:25] Command completed successfully
[14:32:26] Committing changes: "Add useTheme hook"
```

#### Files Tab

Changed files with diff viewer:

```diff
+ src/hooks/useTheme.ts (new)
M src/contexts/ThemeContext.tsx
M src/components/Header.tsx
```

### Terminal View

Monitor agent terminals directly:

1. Navigate to **Terminals** view (press `A`)
2. Watch agent activity in real-time
3. See command outputs and file operations

### WebSocket Events

The UI receives real-time updates via WebSocket:

| Event | Information |
|-------|-------------|
| `task:progress` | Phase and percentage updates |
| `task:status` | Status changes (pending → in_progress) |
| `task:log` | Agent log messages |
| `task:error` | Error notifications |

---

## Intervening and Guiding Agents

### When to Intervene

Consider intervening when:

- Task is stuck for extended periods
- Agent is making repetitive mistakes
- Wrong approach is being taken
- External information is needed

### How to Intervene

#### 1. Stop the Task

From the Task Detail Modal, click **"Stop"** to pause execution.

#### 2. Edit the Spec

Navigate to `.auto-claude/specs/{task-id}/spec.md` and:
- Clarify requirements
- Add constraints
- Provide examples

#### 3. Edit the Implementation Plan

Modify `.auto-claude/specs/{task-id}/implementation_plan.json`:
- Add or remove subtasks
- Change subtask order
- Update acceptance criteria

#### 4. Resume Execution

Click **"Resume"** to continue from where the agent left off.

### Guiding Strategies

#### Provide More Context

Add detailed notes to the spec:

```markdown
## Notes

The theme toggle should follow the pattern used in the existing
UserPreferences component at src/components/UserPreferences.tsx.
Use the existing colorScheme utility functions from src/lib/colors.ts.
```

#### Define Constraints

Be explicit about what NOT to do:

```markdown
## Constraints

- Do NOT create a new state management solution
- Do NOT modify the existing CSS variables
- Must work without JavaScript (CSS fallback)
```

#### Break Down Further

If a subtask is too complex, edit the plan to split it:

```json
{
  "id": "2.3a",
  "title": "Create theme toggle UI component",
  "status": "pending"
},
{
  "id": "2.3b",
  "title": "Wire toggle to theme context",
  "status": "pending",
  "dependencies": ["2.3a"]
}
```

### Manual Worktree Work

You can work directly in the task worktree:

```bash
# Enter the worktree
cd .auto-claude/worktrees/tasks/001-dark-mode/

# Make manual changes
code .  # Open in your editor

# Commit your changes
git add .
git commit -m "Manual fix: correct theme toggle position"

# Return and resume the task from UI
```

---

## Troubleshooting Common Issues

### Task Stuck in Planning

**Symptoms:** Planning phase takes more than 10 minutes.

**Solutions:**
1. Check agent logs for errors
2. Stop and restart the task
3. Simplify the spec
4. Check if similar features exist (agent may be confused)

### Coder Making Wrong Changes

**Symptoms:** Agent modifies wrong files or uses wrong patterns.

**Solutions:**
1. Stop the task
2. Edit spec to reference correct files
3. Add explicit examples of expected patterns
4. Clear incorrect changes in worktree
5. Resume task

### QA Loop Not Completing

**Symptoms:** Task bounces between QA Review and QA Fix repeatedly.

**Solutions:**
1. Check QA report for recurring issues
2. Manually fix the root cause in worktree
3. Simplify acceptance criteria if too strict
4. Move to Human Review if progress stalls (after 10 iterations)

### Tests Failing

**Symptoms:** QA fails due to test failures.

**Solutions:**
1. Check if tests are flaky
2. Verify test environment is configured
3. Check if dependencies are installed
4. Run tests manually in worktree to diagnose

### Merge Conflicts

**Symptoms:** Cannot merge due to conflicts.

**Solutions:**
1. Pull latest changes to base branch
2. Rebase worktree:
   ```bash
   cd .auto-claude/worktrees/tasks/001-task/
   git rebase main
   ```
3. Resolve conflicts manually
4. Retry merge from UI

### Agent Token Expired

**Symptoms:** Tasks fail with authentication errors.

**Solutions:**
1. Run `claude setup-token` in terminal
2. Update `CLAUDE_CODE_OAUTH_TOKEN` in `.env`
3. Restart the web server

---

## Best Practices

### Writing Good Specs

1. **Be specific** - Include exact requirements
2. **Provide examples** - Show what success looks like
3. **Reference existing code** - Point to patterns to follow
4. **Define scope** - Be clear about what's NOT included
5. **Set acceptance criteria** - Make them testable

### Efficient Task Sizing

| Size | Description | Example |
|------|-------------|---------|
| **Small** | Single file, simple change | "Add aria-label to button" |
| **Medium** | Few files, moderate complexity | "Add dark mode toggle" |
| **Large** | Multiple files, significant feature | "Add user authentication" |

**Tip:** Break large tasks into multiple medium tasks for better results.

### Monitoring Habits

- **Check progress regularly** - Don't let tasks run unmonitored
- **Review logs** - Understand what the agent is doing
- **Intervene early** - Don't wait for complete failure
- **Learn patterns** - Note what works for your codebase

### Review Effectively

- **Test in worktree** - Don't just review diffs
- **Run full test suite** - Verify nothing broke
- **Check edge cases** - Try unexpected inputs
- **Verify accessibility** - If UI changes were made

### Maintain Clean State

- **Archive completed tasks** - Keep Kanban board clean
- **Delete empty worktrees** - Free disk space
- **Update base branch** - Keep it current to avoid conflicts
- **Clean spec folders** - Remove failed task specs

---

## Related Guides

- **[Getting Started](GETTING-STARTED.md)** - Installation and first task
- **[Web UI Guide](WEB-UI-GUIDE.md)** - Complete interface reference
- **[CLI Usage](CLI-USAGE.md)** - Terminal-based operations
- **[Troubleshooting](TROUBLESHOOTING.md)** - Common issues and solutions

---

**Claude Code Manager Web** - Master the AI development workflow!
