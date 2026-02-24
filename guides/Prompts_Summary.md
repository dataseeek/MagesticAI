# Auto-Claude Prompts Summary

This document provides a comprehensive overview of all 46 prompt files used by Auto-Claude agents.

## Table of Contents

- [Core Pipeline](#core-pipeline) (5 agents)
- [Spec Creation](#spec-creation) (6 agents)
- [GitHub Integration](#github-integration) (20 agents)
- [Ideation](#ideation) (6 agents)
- [Roadmap](#roadmap) (4 agents)
- [MCP Tools](#mcp-tools) (3 agents)
- [Utility](#utility) (2 agents)

---

## Core Pipeline

The main agents that execute the build process from planning through QA.

### planner.md
- **Purpose**: First agent in autonomous development; creates subtask-based implementation plan from spec
- **Input**: `spec.md`, `project_index.json`, `context.json`
- **Output**: `implementation_plan.json`, `init.sh`, `build-progress.txt`
- **Key Instructions**:
  - MANDATORY Phase 0: Deep codebase investigation before planning
  - Understand workflow type: feature, refactor, investigation, migration, or simple
  - Create phases respecting service dependencies
  - Add verification strategy and QA acceptance criteria
  - Do NOT implement code - planning only

### coder.md
- **Purpose**: Implements subtasks defined in implementation plan one at a time
- **Input**: `implementation_plan.json`, `spec.md`, `context.json`, session memory files
- **Output**: Code changes, git commits, updated `implementation_plan.json`
- **Key Instructions**:
  - MANDATORY Step 1: Get bearings - read all context files
  - Mark subtask as in_progress before coding
  - Use subagents for parallel complex work (up to 10 concurrent)
  - Run self-critique checklist before marking complete
  - Verify subtask using verification method from plan
  - Fix bugs immediately - next session has no memory

### coder_recovery.md
- **Purpose**: Recovery awareness for stuck or previously-attempted subtasks
- **Input**: `attempt_history.json`, `current_approach.txt`, previous attempt records
- **Output**: Updated attempt history, different approach strategy
- **Key Instructions**:
  - Check attempt_history.json BEFORE implementing
  - If subtask has previous attempts: MUST try DIFFERENT approach
  - Record approach before implementation
  - Mark stuck if 3+ attempts fail with different approaches

### qa_reviewer.md
- **Purpose**: Quality assurance validation before sign-off
- **Input**: Complete implementation with all subtasks marked completed
- **Output**: `qa_report.md`, updated `implementation_plan.json` with qa_signoff status
- **Key Instructions**:
  - Verify all subtasks completed
  - Run automated tests (unit, integration, E2E)
  - Browser verification if frontend involved
  - Code review including security (OWASP Top 10)
  - Use Context7 to validate third-party API/library usage
  - If REJECTED: Create `QA_FIX_REQUEST.md` with detailed issues

### qa_fixer.md
- **Purpose**: Fixes issues identified by QA Reviewer
- **Input**: `QA_FIX_REQUEST.md` with specific issues and locations
- **Output**: Fixed code, commit with qa-requested tag
- **Key Instructions**:
  - Parse all required fixes from QA_FIX_REQUEST.md
  - Fix issues one by one (not all at once)
  - Make MINIMAL changes - don't refactor or add features
  - Verify each fix locally
  - Loop continues until QA approves or max iterations reached

---

## Spec Creation

Agents that create and refine specifications before implementation begins.

### spec_gatherer.md
- **Purpose**: Understand user requirements and create structured requirements file
- **Input**: Task description (user input), `project_index.json`
- **Output**: `requirements.json`
- **Key Instructions**:
  - Confirm understanding or ask for clarification
  - Determine workflow type (feature, refactor, investigation, migration, simple)
  - Identify involved services
  - MUST create requirements.json - orchestrator checks for it

### spec_researcher.md
- **Purpose**: Research and validate external integrations, libraries, and dependencies
- **Input**: `requirements.json` with mentioned integrations
- **Output**: `research.json` with validated findings
- **Key Instructions**:
  - Use Context7 MCP as primary research tool
  - Resolve library IDs and get documentation
  - Extract correct package names, imports, initialization, APIs
  - Don't make up APIs - only document what found in docs

### spec_writer.md
- **Purpose**: Create complete spec.md specification document
- **Input**: `project_index.json`, `requirements.json`, `context.json`
- **Output**: `spec.md` with all required sections
- **Key Instructions**:
  - Load all input files and extract key information
  - Write spec with exact template structure
  - Include: Overview, Workflow Type, Requirements, Implementation Notes
  - QA Acceptance Criteria is CRITICAL for QA agent
  - NO user interaction needed

### spec_critic.md
- **Purpose**: Deep analysis and fixing of spec.md before implementation
- **Input**: `spec.md`, `research.json`, `requirements.json`, `context.json`
- **Output**: Fixed `spec.md`, `critique_report.json`
- **Key Instructions**:
  - Use extended thinking (ultrathink) for deep analysis
  - Check technical accuracy against research.json
  - Use Context7 to verify API patterns
  - Fix issues directly in spec.md
  - Severity levels: HIGH, MEDIUM, LOW

### spec_quick.md
- **Purpose**: Create minimal, focused spec for simple tasks
- **Input**: Task description for simple change
- **Output**: Minimal `spec.md` (20-50 lines), simple `implementation_plan.json`
- **Key Instructions**:
  - For straightforward changes (typos, colors, text updates)
  - Create concise spec with only essential sections
  - Create simple plan with 1 phase and 1 subtask
  - Do NOT over-engineer

### complexity_assessor.md
- **Purpose**: Analyze task and determine correct complexity level
- **Input**: `requirements.json`
- **Output**: `complexity_assessment.json` with complexity tier
- **Key Instructions**:
  - Analyze 5 dimensions: Scope, Integration, Infrastructure, Knowledge, Risk
  - Complexity Tiers:
    - TRIVIAL: 1 file, no logic → 3 phases
    - SIMPLE: 1-2 files → 3-4 phases
    - STANDARD: 3-10 files → 6-7 phases
    - COMPLEX: 10+ files → 8 phases (includes research + critique)

---

## GitHub Integration

Agents for PR review, issue management, and follow-up actions.

### PR Review Core

| Agent | Purpose |
|-------|---------|
| **pr_reviewer.md** | Senior engineer code review with security focus (OWASP Top 10) |
| **pr_orchestrator.md** | Coordinates multiple review agents |
| **pr_parallel_orchestrator.md** | Runs reviews in parallel for efficiency |
| **pr_ai_triage.md** | Categorizes PR for appropriate handling |

### Specialized Review Agents

| Agent | Purpose |
|-------|---------|
| **pr_quality_agent.md** | Code quality metrics and patterns |
| **pr_security_agent.md** | Security vulnerability scanning |
| **pr_logic_agent.md** | Business logic and correctness verification |
| **pr_structural.md** | Architecture and design patterns |
| **pr_codebase_fit_agent.md** | Integration with existing patterns |

### Issue Management

| Agent | Purpose |
|-------|---------|
| **issue_analyzer.md** | Analyzes GitHub issues in detail |
| **issue_triager.md** | Categorizes and prioritizes issues |
| **duplicate_detector.md** | Finds duplicate issues |
| **spam_detector.md** | Identifies spam/invalid issues |

### PR Follow-Up & Fixes

| Agent | Purpose |
|-------|---------|
| **pr_fixer.md** | Fixes issues found in code review |
| **pr_finding_validator.md** | Validates review findings |
| **pr_followup.md** | General follow-up handling |
| **pr_followup_orchestrator.md** | Coordinates follow-up actions |
| **pr_followup_comment_agent.md** | Generates review comments |
| **pr_followup_newcode_agent.md** | Handles new code in follow-ups |
| **pr_followup_resolution_agent.md** | Resolves all identified issues |

---

## Ideation

Agents that generate improvement ideas for specific domains.

| Agent | Purpose | Focus Area |
|-------|---------|------------|
| **ideation_code_improvements.md** | Suggest code enhancements | Refactoring, optimization |
| **ideation_code_quality.md** | Improve code standards | Patterns, best practices |
| **ideation_documentation.md** | Documentation improvements | Comments, READMEs, guides |
| **ideation_performance.md** | Performance optimizations | Speed, memory, efficiency |
| **ideation_security.md** | Security enhancements | Vulnerabilities, hardening |
| **ideation_ui_ux.md** | UI/UX improvements | Usability, accessibility |

---

## Roadmap

Agents for project roadmap generation and strategic planning.

### roadmap_discovery.md
- **Purpose**: Understand project purpose, audience, and current state
- **Input**: `project_index.json`, README, package files
- **Output**: `roadmap_discovery.json`
- **Key Instructions**:
  - Autonomously analyzes (NO user interaction)
  - Incorporates competitor insights if available

### roadmap_features.md
- **Purpose**: Generate strategic, prioritized feature list
- **Input**: `roadmap_discovery.json`, `project_index.json`
- **Output**: `roadmap.json` with features organized by phases
- **Key Instructions**:
  - MoSCoW prioritization (Must, Should, Could, Won't)
  - Link features to competitor pain points
  - Create meaningful milestones per phase

### competitor_analysis.md
- **Purpose**: Research competitors and user feedback from competitor products
- **Input**: `roadmap_discovery.json`
- **Output**: `competitor_analysis.json`
- **Key Instructions**:
  - Use WebSearch for alternatives and reviews
  - Extract pain points and market gaps
  - Document sources meticulously

### followup_planner.md
- **Purpose**: Add new subtasks to completed spec (extend, don't replace)
- **Input**: `FOLLOWUP_REQUEST.md`, completed `implementation_plan.json`
- **Output**: Updated `implementation_plan.json` with new phases
- **Key Instructions**:
  - CRITICAL: Preserve all existing phases and subtasks
  - Continue phase numbering from where previous left off
  - Keep existing subtask statuses

---

## MCP Tools

Specialized agents for validation using MCP (Model Context Protocol) tools.

| Agent | Purpose | Tools Used |
|-------|---------|------------|
| **api_validation.md** | Validates REST API implementations | HTTP testing |
| **database_validation.md** | Validates database operations | SQL queries |
| **puppeteer_browser.md** | Browser automation and testing | Puppeteer MCP |

---

## Utility

Support agents for learning and maintenance.

### insight_extractor.md
- **Purpose**: Extract learnings from completed sessions for memory system
- **Input**: Git diff, subtask description, attempt history, session outcome
- **Output**: JSON with file insights, patterns, gotchas, recommendations
- **Key Instructions**:
  - Extract ACTIONABLE knowledge only
  - Document patterns discovered with examples
  - Record gotchas with trigger and solution
  - Output only JSON, no markdown wrapping

### validation_fixer.md
- **Purpose**: Fix validation errors in spec files
- **Input**: Validation error message, failed file
- **Output**: Fixed file passing validation
- **Key Instructions**:
  - Make MINIMAL changes - don't restructure
  - Preserve valid existing data
  - Fix one error at a time, then verify

---

## Summary Table

| Category | Agent | Input | Output |
|----------|-------|-------|--------|
| **Core** | planner | spec.md | implementation_plan.json |
| | coder | impl_plan.json | Code + commits |
| | coder_recovery | attempt_history.json | New approach |
| | qa_reviewer | Code | qa_report.md |
| | qa_fixer | QA_FIX_REQUEST.md | Fixes |
| **Spec** | spec_gatherer | Task description | requirements.json |
| | spec_researcher | requirements.json | research.json |
| | spec_writer | Context files | spec.md |
| | spec_critic | spec.md | Fixed spec.md |
| | spec_quick | Simple task | Minimal spec.md |
| | complexity_assessor | requirements.json | complexity_assessment.json |
| **Roadmap** | roadmap_discovery | project_index.json | roadmap_discovery.json |
| | roadmap_features | discovery.json | roadmap.json |
| | competitor_analysis | discovery.json | competitor_analysis.json |
| | followup_planner | FOLLOWUP_REQUEST.md | Updated plan |
| **Utility** | insight_extractor | Diff + outcome | insight JSON |
| | validation_fixer | Error message | Fixed file |

---

## Pipeline Flow

```
User Request
    │
    ▼
┌─────────────────────────────────────────────────────┐
│                  SPEC CREATION                       │
│  gatherer → researcher → writer → critic            │
│     (or spec_quick for simple tasks)                │
└─────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────┐
│                  CORE PIPELINE                       │
│  planner → coder (loop) → qa_reviewer → qa_fixer   │
│              ↑_______________|                       │
└─────────────────────────────────────────────────────┘
    │
    ▼
  Complete
```

---

*Generated from `apps/backend/prompts/` - 46 prompt files total*
