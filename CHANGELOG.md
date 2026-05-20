## 2.2.0 - 2026-05-20

### ✨ Added
- **OpenAI-Compatible LLM Endpoints (#42, closes #39)**: First-class support for any OpenAI-compatible server (LM Studio, vLLM, OpenRouter, Together, Groq, LocalAI, Anyscale, and Ollama at `:11434/v1`). New `GET /settings/openai-compat/models` and `POST /settings/openai-compat/test` endpoints. Provider-choice + OpenAI-compat steps in onboarding. `openai_compat` available across the settings model, agent profiles, and every provider dropdown.
- **Up-to-date cloud-provider model lists (#45)**: Refreshed Claude / Codex / Gemini catalogs to current generation — Opus 4.7, GPT-5.5, GPT-5.3-Codex, Gemini 3.5 Flash stable, Gemini 3.1 Flash-Lite. Dropped superseded entries (GPT-5.2-Codex, GPT-5.1-Codex-Max/Mini, Gemini 3 Flash preview).

### 🛠️ Fixed
- **NameError crash in settings routes (#41)**: Added the missing module-level `logger` in `settings.py`, fixing crashes in Ollama / OAuth error paths.
- **Files tab in self-host mode (#40)**: `.magestic-ai/` subtrees are now reachable when the target project IS MagesticAI itself (dogfooding) — the `_is_app_internal_path` guard previously blocked legitimate spec data.
- **"Merge to Main" button label (#43)**: Footer button and progress indicator now show the actual target branch (e.g. "Merge to dev") instead of a hardcoded "main".

### 🔧 Changed
- **Simplified LLM Providers settings page (#46)**: Restructured from three confusing panels to two — **Cloud Agents** (Claude / Codex / Gemini CLI logins) and **OpenAI-Compatible Endpoints** (covers LM Studio, vLLM, Together, Groq, and Ollama at `:11434/v1`). Removed the QA Provider panel (dead UI — actual QA execution reads the model from Agent Settings phase config, not the dropped `qaLlmProvider` setting). Removed the Local LLMs panel and the top-header Ollama status badge (Ollama now consumed via OpenAI-compat). Anthropic icon replaced with a neutral Cloud icon on the multi-vendor Cloud Agents panel.

### 📦 Updated
- **CLAUDE.md path references (#44)**: Updated documentation from legacy `.auto-claude/` to the canonical `.magestic-ai/` everywhere — the code has been using the new paths for a while.

---

## 2.1.0

### ✨ Added
- **GitHub PR Review Integration**: End-to-end support for PR reviews including listing, fetching, posting reviews, checking new commits, and viewing logs via dedicated API endpoints.
- **PR Review WebSocket Events**: Real-time progress, completion, and error events via WebSocket for live feedback during PR reviews.
- **PR Action Endpoints**: Support for posting reviews, commenting, merging, assigning, and canceling PRs through backend API.
- **AI-Powered Conflict Resolution**: Enhanced "Fix Conflicts with AI" functionality with real git merge and AI resolution of conflict markers.
- **Task from Chat Feature**: Button in Insights chat to convert conversation into a structured task (title + PRD description) with editable preview.
- **Open in Browser**: New "Open in Browser" button in EditorPage that serves files with correct MIME types and asset URL rewriting.
- **QA Fixer Phase**: Added separate `qa_fixer` phase in phase configuration, allowing independent model and thinking settings.
- **Phase-Scaled Progress**: Monotonically increasing progress percentages across phases (planning 0–20%, coding 20–80%, QA 80–95%, complete 95–100%).
- **Terminal Persistence**: TerminalGrid now remains mounted across view switches to prevent stuck terminals and lost PTY connections.
- **Model & Token Metrics**: Display assistant model name on chat messages and show tokens/sec metrics after each response across all providers.
- **Dark Theme & UI Improvements**: Enhanced folder navigation, keyboard support (Enter/Backspace), HTML preview, progress labels, and overall dark theme consistency.

### 🛠️ Fixed
- **GitHub PR Connection Detection**: Fixed incorrect endpoint call (`window.API.github.checkGitHubConnection` → `window.API.checkGitHubConnection`).
- **AI Merge Conflict Resolution**: Fixed syntax error in `github.py` caused by AI-generated extra closing brace.
- **requireReviewBeforeCoding Sync**: Ensured field is written to `task_metadata.json` when editing tasks.
- **Email Notifications**: Fixed silent failure under legacy token auth by populating default user context.
- **Build Progress & Subtask Status**: Added fallback in `post_session_processing` to detect new commits and force-update status.
- **File Serving 404s**: Resolved `404` errors for `/api/files/serve` by properly staging the endpoint and enabling public access with path-traversal protection.
- **Model Config Loss**: Fixed `UpdateModelConfigRequest` to preserve all fields (provider, profileId, model, thinkingLevel, temperature).
- **Issue-to-Task Creation**: Fixed backend `TaskMetadata` model to include `githubIssueNumber`, `affectedFiles`, and `acceptanceCriteria`.
- **Sidebar Layout**: Restored proper layout and spacing in sidebar components.

### 🔧 Changed
- **Project Renaming**: Renamed from "Claude Code Manager Web" to **MagesticAI** across UI, navigation, and documentation.
- **MCP Template Filtering**: Removed redundant and duplicate quick templates (filesystem, fetch, github, gitlab) that conflict with native tools.
- **Hardcoded Model Values**: Replaced inline model/thinking defaults with shared constants to ensure user-configured settings take effect.
- **Git Ignore Safety**: Added `.magestic-ai-security.json` and `.magestic-ai-status` to `.gitignore` during project init and unstage during merges.
- **CLI Detection Optimization**: Improved speed using `shutil.which` and `npm package.json` parsing instead of slow Node.js startup (~4s → <50ms).

### 📦 Updated
- **README.md**: Updated project documentation with fixed GitHub URL, removed non-existent files, and added Docker deployment guide.
- **Phase Progress Logic**: Refactored progress logic to prevent backward jumps between phases using defined phase ranges.