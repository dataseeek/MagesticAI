# Changelog

## 2.2.0 - 2026-05-20

### ✨ Added
- **OpenAI-Compatible LLM Endpoints (#42, closes #39)**: First-class support for any OpenAI-compatible server (LM Studio, vLLM, OpenRouter, Together, Groq, LocalAI, Anyscale, and Ollama at `:11434/v1`). New `GET /settings/openai-compat/models` and `POST /settings/openai-compat/test` endpoints. Provider-choice + OpenAI-compat steps in onboarding. `openai_compat` available across the settings model, agent profiles, and every provider dropdown.
- **Up-to-date cloud-provider model lists (#45)**: Refreshed Claude / Codex / Gemini catalogs to current generation — Opus 4.7, GPT-5.5, GPT-5.3-Codex, Gemini 3.5 Flash stable, Gemini 3.1 Flash-Lite. Dropped superseded entries (GPT-5.2-Codex, GPT-5.1-Codex-Max/Mini, Gemini 3 Flash preview).
- **Auto-release workflow (#48)**: New `.github/workflows/release.yml` auto-creates the git tag and GitHub release whenever `package.json#version` changes on a push to `main`. Validates `CHANGELOG.md` has a matching section, extracts release notes, and skips out cleanly on non-release merges.

### 🛠️ Fixed
- **NameError crash in settings routes (#41)**: Added the missing module-level `logger` in `settings.py`, fixing crashes in Ollama / OAuth error paths.
- **Files tab in self-host mode (#40)**: `.magestic-ai/` subtrees are now reachable when the target project IS MagesticAI itself (dogfooding) — the `_is_app_internal_path` guard previously blocked legitimate spec data.
- **"Merge to Main" button label (#43)**: Footer button and progress indicator now show the actual target branch (e.g. "Merge to dev") instead of a hardcoded "main".

### 🔧 Changed
- **Simplified LLM Providers settings page (#46)**: Restructured from three confusing panels to two — **Cloud Agents** (Claude / Codex / Gemini CLI logins) and **OpenAI-Compatible Endpoints** (covers LM Studio, vLLM, Together, Groq, and Ollama at `:11434/v1`). Removed the QA Provider panel (dead UI — actual QA execution reads the model from Agent Settings phase config, not the dropped `qaLlmProvider` setting). Removed the Local LLMs panel and the top-header Ollama status badge (Ollama now consumed via OpenAI-compat). Anthropic icon replaced with a neutral Cloud icon on the multi-vendor Cloud Agents panel.

### 📦 Updated
- **CLAUDE.md path references (#44)**: Updated documentation from legacy `.auto-claude/` to the canonical `.magestic-ai/` everywhere — the code has been using the new paths for a while.


## 2.1.0 — 2026-05-20

### ✨ Added
- **OpenAI-Compatible LLM Endpoints**: First-class support for any service speaking the OpenAI `/v1/chat/completions` protocol — LM Studio, vLLM, OpenRouter, Together AI, Groq, LocalAI, Anyscale. Includes a text-only provider and an agentic provider with full tool-calling support. Endpoint config persists in SQLite and is editable via Settings → Claude Code Accounts.
- **Endpoint Status Badge**: New Globe-icon badge in the header showing connection status (green/red/gray) per saved endpoint, with a popover detailing label, base URL, default model, and an inline Test button. Auto-probes every 5 minutes.
- **Model Picker Integration**: Saved OpenAI-compatible endpoints appear in the agent profile model dropdown alongside Claude / Codex / Gemini / Ollama. Embedding-only models are filtered out automatically.
- **Comparison Table in README**: New "How does it compare?" section positioning MagesticAI against Spec Kit and Compozy.

### 🛠️ Fixed
- **Implementation Plan Validator Resilience**: The spec validator now returns a structured error when an LLM emits `phases` as a dict instead of a list (common with smaller local models like qwen3-14b), instead of crashing with `AttributeError`. The existing validation-fixer retry loop then asks the model to repair the schema. Six new regression tests pin the behaviour.
- **DISABLE_AUTH Middleware**: When `APP_DISABLE_AUTH=true` (development mode), the auth middleware now populates `request.state.user` with the default user, so routes using `Depends(get_current_user)` work correctly in dev. Previously they returned 401.
- **QA Loop Provider Resolution**: The QA reviewer and fixer now pass `base_url` / `api_key` through to the OpenAI-compatible provider via the new endpoint resolution helper, instead of silently defaulting to `api.openai.com` with no auth.

### 🔧 Changed
- **Settings: "LLM Accounts" → "Claude Code Accounts"**: Renamed the settings section title across all three locales (en / fr / pt-BR) to reflect its actual scope.
- **Dependabot Mode**: Removed `.github/dependabot.yml`. Only security-CVE-driven alerts remain (GitHub default for public repos); routine version-update PRs are off.
- **README Structure**: New "OpenAI-Compatible Endpoints" subsection in Configuration with a small-model caveat. New "How does it compare?" section between Supported Platforms and Quick Start.
- **CLAUDE.md Branching Guidance**: Spelled out the dev-first branching model — `dev` is the working branch, `main` is release-only. Fixed the Contributing section's stale reference to "develop" (the actual branch is `dev`).

---

## 2.0.0 — 2026-03-02

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
