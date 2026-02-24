# Status and Phases Reference

This document describes all status and phase values used in Claude Code Manager Web.

## Task Status (`TaskStatus`)

Main status for tasks in the system.

| Status | Description |
|--------|-------------|
| `backlog` | Task waiting to be started |
| `in_progress` | Task currently executing |
| `ai_review` | AI is reviewing the task |
| `human_review` | Requires human review |
| `done` | Task completed |

**Location:** `apps/frontend-web/src/shared/types/task.ts:8`

---

## Review Reason (`ReviewReason`)

Explains why a task is in `human_review` status.

| Reason | Description |
|--------|-------------|
| `completed` | All subtasks done, QA passed, ready for final approval/merge |
| `errors` | Subtasks failed during execution |
| `qa_rejected` | QA found issues that need fixing |
| `plan_review` | Spec/plan created and awaiting approval before coding starts |

**Location:** `apps/frontend-web/src/shared/types/task.ts:15`

---

## Execution Phase (`ExecutionPhase`)

Real-time execution progress phases. Used for tracking task progress during execution.

| Phase | Order Index | Description |
|-------|-------------|-------------|
| `idle` | -1 | Initial state before any backend events (frontend only) |
| `spec_creation` | -0.5 | Creating implementation plan/spec |
| `planning` | 0 | Planning phase |
| `plan_review` | 0.5 | Paused for human plan approval |
| `coding` | 1 | Implementing code |
| `qa_review` | 2 | QA reviewing changes |
| `qa_fixing` | 3 | Fixing QA issues |
| `complete` | 4 | Successfully completed |
| `failed` | 99 | Task failed (error state) |

**Terminal Phases:** `complete`, `failed` - Cannot be changed by fallback text matching.

**Location:** `apps/frontend-web/src/shared/constants/phase-protocol.ts`

**Protocol:** Phase events are communicated via: `__EXEC_PHASE__:{"phase":"coding","message":"Starting"}`

---

## Subtask Status (`SubtaskStatus`)

Status for individual subtasks within a task.

| Status | Description |
|--------|-------------|
| `pending` | Subtask not yet started |
| `in_progress` | Currently being executed |
| `completed` | Successfully completed |
| `failed` | Subtask failed |

**Location:** `apps/frontend-web/src/shared/types/task.ts:17`

---

## Task Log Phase (`TaskLogPhase`)

Phases for persistent, phase-based logging.

| Phase | Description |
|-------|-------------|
| `planning` | Planning phase logs |
| `coding` | Coding phase logs |
| `validation` | Validation/QA phase logs |

**Location:** `apps/frontend-web/src/shared/types/task.ts:60`

---

## Task Log Phase Status (`TaskLogPhaseStatus`)

Status for each log phase.

| Status | Description |
|--------|-------------|
| `pending` | Phase not started |
| `active` | Phase currently active |
| `completed` | Phase completed successfully |
| `failed` | Phase failed |

**Location:** `apps/frontend-web/src/shared/types/task.ts:61`

---

## Task Log Entry Type (`TaskLogEntryType`)

Types of log entries.

| Type | Description |
|------|-------------|
| `text` | Plain text log entry |
| `tool_start` | Tool execution started |
| `tool_end` | Tool execution ended |
| `phase_start` | Phase started |
| `phase_end` | Phase ended |
| `error` | Error message |
| `success` | Success message |
| `info` | Informational message |

**Location:** `apps/frontend-web/src/shared/types/task.ts:62`

---

## QA Report Status

Status for QA validation reports.

| Status | Description |
|--------|-------------|
| `passed` | QA validation passed |
| `failed` | QA validation failed |
| `pending` | QA validation pending |

**Location:** `apps/frontend-web/src/shared/types/task.ts:45-49`

---

## QA Issue Severity

Severity levels for QA issues.

| Severity | Description |
|----------|-------------|
| `critical` | Critical issue, must be fixed |
| `major` | Major issue, should be fixed |
| `minor` | Minor issue, nice to fix |

**Location:** `apps/frontend-web/src/shared/types/task.ts:51-57`

---

## Task Metadata Types

### Task Complexity (`TaskComplexity`)
| Value | Description |
|-------|-------------|
| `trivial` | Very simple, single change |
| `small` | Small feature/fix |
| `medium` | Medium complexity |
| `large` | Large feature |
| `complex` | Complex system change |

### Task Impact (`TaskImpact`)
| Value | Description |
|-------|-------------|
| `low` | Low impact |
| `medium` | Medium impact |
| `high` | High impact |
| `critical` | Critical impact |

### Task Priority (`TaskPriority`)
| Value | Description |
|-------|-------------|
| `low` | Low priority |
| `medium` | Medium priority |
| `high` | High priority |
| `urgent` | Urgent priority |

### Task Category (`TaskCategory`)
| Value | Description |
|-------|-------------|
| `feature` | New feature |
| `bug_fix` | Bug fix |
| `refactoring` | Code refactoring |
| `documentation` | Documentation |
| `security` | Security improvement |
| `performance` | Performance optimization |
| `ui_ux` | UI/UX improvement |
| `infrastructure` | Infrastructure change |
| `testing` | Testing improvement |

**Location:** `apps/frontend-web/src/shared/types/task.ts:157-172`

---

## File Locations

| File | Purpose |
|------|---------|
| `apps/frontend-web/src/shared/types/task.ts` | Task type definitions |
| `apps/frontend-web/src/shared/constants/phase-protocol.ts` | Execution phase constants and helpers |
| `apps/backend/core/phase_event.py` | Backend phase event emitter (must sync with frontend) |
