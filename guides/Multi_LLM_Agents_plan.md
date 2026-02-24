# Plan: Multi-Model AI Integration (Gemini/Codex)

## Goal
Integrate `@agent-gemini-research-analyst` and `@agent-codex-research-analyst` into the Auto-Claude pipeline for alternative perspectives at key decision points.

## Integration Architecture

```
                    ┌─────────────────┐
                    │  Model Router   │
                    │  (selects AI)   │
                    └────────┬────────┘
           ┌─────────────────┼─────────────────┐
           ▼                 ▼                 ▼
    ┌──────────┐      ┌──────────┐      ┌──────────┐
    │  Claude  │      │  Gemini  │      │  Codex   │
    │ (primary)│      │(research)│      │ (code)   │
    └──────────┘      └──────────┘      └──────────┘
           │                 │                 │
           └─────────────────┼─────────────────┘
                             ▼
                    ┌─────────────────┐
                    │ Result Merger   │
                    │ (combine views) │
                    └─────────────────┘
```

## Integration Points by Phase

### 1. Spec Critic (Parallel Review)
- **Claude**: Deep technical critique
- **Gemini**: Alternative perspective, web validation
- **Output**: Merged critique with both viewpoints

### 2. QA Reviewer (Multi-Model Review)
- **Claude**: Primary code review
- **Codex**: Code-focused analysis (OpenAI strength)
- **Output**: Combined QA report

### 3. Competitor Analysis (Research Enhancement)
- **Gemini**: Web search, current market data
- **Claude**: Synthesis and strategic analysis
- **Output**: Research + analysis combined

### 4. Spec Researcher (Cross-Validation)
- **Claude**: Context7 library research
- **Gemini**: Web search for alternatives, gotchas
- **Output**: Validated research findings

### 5. Complexity Assessor (Decision Validation)
- **Claude**: Primary assessment
- **Codex**: Second estimate
- **Output**: Average + flag if >30% discrepancy

### 6. PR Reviewer (Critical PRs Only)
- **Claude**: Security + logic review
- **Gemini/Codex**: Quality + patterns review
- **Output**: Multi-perspective findings

## Implementation Options

### Option A: Sequential (Simple)
```python
# Run Claude first, then alternative model
claude_result = await run_claude_agent(prompt)
gemini_result = await run_gemini_agent(prompt)
merged = merge_results(claude_result, gemini_result)
```

### Option B: Parallel (Faster)
```python
# Run both simultaneously
results = await asyncio.gather(
    run_claude_agent(prompt),
    run_gemini_agent(prompt)
)
merged = merge_results(*results)
```

### Option C: Conditional (Smart)
```python
# Only invoke second model when needed
claude_result = await run_claude_agent(prompt)
if needs_second_opinion(claude_result):
    gemini_result = await run_gemini_agent(prompt)
    merged = merge_results(claude_result, gemini_result)
```

## Files to Create/Modify

### New Files
1. `apps/backend/core/model_router.py` - Route requests to appropriate model
2. `apps/backend/core/result_merger.py` - Merge multi-model outputs
3. `apps/backend/core/model_context.py` - Context builder for external models
4. `apps/backend/integrations/gemini_client.py` - Gemini API wrapper
5. `apps/backend/integrations/codex_client.py` - OpenAI/Codex API wrapper

### Modified Prompts (add multi-model support)
1. `prompts/spec_critic.md` - Add merge instructions
2. `prompts/qa_reviewer.md` - Add parallel review output format
3. `prompts/competitor_analysis.md` - Add research source attribution
4. `prompts/complexity_assessor.md` - Add discrepancy handling

### Configuration
```python
# config.py
MULTI_MODEL_CONFIG = {
    "spec_critic": ["claude", "gemini"],
    "qa_reviewer": ["claude", "codex"],
    "competitor_analysis": ["gemini", "claude"],
    "spec_researcher": ["claude", "gemini"],
    "complexity_assessor": ["claude", "codex"],
    "pr_reviewer": ["claude"],  # Optional second model
}
```

## Result Merge Strategies

| Phase | Merge Strategy |
|-------|----------------|
| spec_critic | Union of findings, deduplicate |
| qa_reviewer | Severity-weighted merge |
| competitor_analysis | Claude synthesis of Gemini research |
| complexity_assessor | Average scores, flag discrepancies |
| pr_reviewer | Categorize by reviewer |

## Model Selection Logic

```python
def select_model(phase: str, task_type: str) -> list[str]:
    if task_type == "research":
        return ["gemini", "claude"]  # Gemini for web, Claude for synthesis
    elif task_type == "code_review":
        return ["claude", "codex"]   # Both strong at code
    elif task_type == "critique":
        return ["claude", "gemini"]  # Different reasoning styles
    else:
        return ["claude"]  # Default to Claude
```

## Environment Variables
```bash
# .env additions
GEMINI_API_KEY=your-gemini-key
OPENAI_API_KEY=your-openai-key  # For Codex
MULTI_MODEL_ENABLED=true
MULTI_MODEL_PARALLEL=true
```

---

## Context Injection Requirements (CRITICAL)

External models (Gemini/Codex) need project context to provide useful analysis.

### Files to Include

| File | Purpose | Include |
|------|---------|---------|
| `README.md` | Architecture overview, task lifecycle | Always |
| `DOCS.md` | Technical details, API patterns, security model | Always |
| `CLAUDE.md` | Has API key references that confuse | Never |
| Task spec files | Specific context for review | Per-task |

### Context Template for External Models

```python
def build_external_model_context(task_spec_dir: Path) -> str:
    """Build context string for Gemini/Codex agents."""

    project_root = Path(".")

    context = f"""
## PROJECT OVERVIEW (from README.md)
{(project_root / "README.md").read_text()[:2000]}

## TECH STACK & PATTERNS (from DOCS.md)
Architecture: React 19 + FastAPI + Claude Agent SDK
Auth: OAuth tokens via `claude setup-token` (NOT API keys)
Storage: File-based (.auto-claude/specs/, ~/.auto-claude-web/)
Security: 3-layer (sandbox, filesystem, command allowlist)

## TASK TO REVIEW
{(task_spec_dir / "spec.md").read_text()}

## REQUIREMENTS
{(task_spec_dir / "requirements.json").read_text()}
"""
    return context
```

### Why This Matters

| Analysis | Without Context | With Context |
|----------|-----------------|--------------|
| Auth review | "Add API key encryption" | Understands OAuth model |
| File ops | "Add file locking" | Knows worktree isolation |
| Patterns | Generic suggestions | Matches existing code |
| Testing | Generic pyramid | FastAPI + WebSocket specific |

### Implementation Location

New file: `apps/backend/core/model_context.py`
- `build_context_for_gemini()` - Research-focused context
- `build_context_for_codex()` - Code-focused context
- `get_project_summary()` - Cached README/DOCS summary

---

## Simulation Results (Task 012 - Real Data)

### Test Case: spec_critic phase with real task 012 files

**Input Files:**
- `spec.md`: 13 lines (minimal, vague acceptance criteria)
- `requirements.json`: 15 lines (category: bug_fix, complexity: small)
- `implementation_plan.json`: 850+ lines (15 phases, 65 subtasks, 46 endpoints)

### Gemini Analysis (Strategic Focus)
| Metric | Finding |
|--------|---------|
| Spec Quality | 2/10 - "violates fundamental principles" |
| Key Issue | Missing domain context, vague criteria |
| Alternative | Domain-driven phases, spike-first approach |
| Recommendation | "CONDITIONAL PROCEED - fix spec first" |

### Codex Analysis (Technical Focus)
| Metric | Finding |
|--------|---------|
| Complexity Mismatch | 625-1500% (small -> 100-120 dev days) |
| Security Issue | Plaintext API keys, no file locking |
| Technical Debt | 59-112 days to fix |
| Recommendation | Split into 009A (fixes) + 009B (AI infra) |

### Comparison: What Each Model Found

| Aspect | Gemini (Strategic) | Codex (Technical) |
|--------|-------------------|-------------------|
| Spec Quality | 2/10 rating | 625-1500% scope variance |
| Security | Auth gaps noted | Plaintext credentials code |
| Structure | Alternative phases | Atomic file operations |
| Testing | "Afterthought" | 71% incomplete, no unit tests |
| Verdict | Fix spec first | Split task, add critical fixes |

### Merged Insights (Multi-Model Value)
1. **Both models identified spec quality issues** - Validates spec_critic use case
2. **Gemini provided strategic alternatives** (domain-driven phases)
3. **Codex provided code-level security patterns** (atomic writes, encryption)
4. **Combined estimate**: 17-27 days to production-ready

### Simulation Conclusion
Multi-model review caught issues that might be missed with single-model:
- Gemini: "Better to implement 7 endpoints correctly than 46 incorrectly"
- Codex: "Current file ops unsafe - race conditions, no encryption"

**Both agree**: Task 012 needs spec refinement before proceeding

---

## Next Steps (When Ready to Implement)

### Phase 1: Context Infrastructure
1. Create `apps/backend/core/model_context.py` - Context builder for external models
2. Add `get_project_summary()` with caching (README.md + DOCS.md)
3. Test context injection with manual Gemini/Codex calls

### Phase 2: Model Clients
4. Create `apps/backend/integrations/gemini_client.py` - Gemini API wrapper
5. Create `apps/backend/integrations/codex_client.py` - OpenAI wrapper
6. Add environment variables: `GEMINI_API_KEY`, `OPENAI_API_KEY`

### Phase 3: Router & Merger
7. Create `apps/backend/core/model_router.py` - Route requests to models
8. Create `apps/backend/core/result_merger.py` - Merge multi-model outputs
9. Implement merge strategies per phase (union, severity-weighted, average)

### Phase 4: Integration
10. Update `prompts/spec_critic.md` - Add multi-model output format
11. Update `prompts/qa_reviewer.md` - Add parallel review support
12. Add configuration UI in web frontend (optional models toggle)

---

## Status: SAVED FOR LATER
- Plan validated with real task 012 simulation
- Context injection requirements documented
- Ready to implement when prioritized

*Created: 2026-01-07*
