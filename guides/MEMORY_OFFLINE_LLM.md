# Memory, LLM & Embeddings Architecture

This document explains how Magestic AI uses memory systems, LLMs, and embeddings for cross-session learning and intelligent code generation.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Current Architecture](#2-current-architecture)
3. [Claude Agent SDK (Primary LLM)](#3-claude-agent-sdk-primary-llm)
4. [Memory System](#4-memory-system)
5. [LLM Providers for Memory](#5-llm-providers-for-memory)
6. [Embedder Providers](#6-embedder-providers)
7. [Offline/Local Setup (Ollama)](#7-offlinelocal-setup-ollama)
8. [Configuration Examples](#8-configuration-examples)
9. [Memory Storage Structure](#9-memory-storage-structure)
10. [Key Source Files](#10-key-source-files)

---

## 1. Architecture Overview

Magestic AI uses a **dual-layer architecture**:

1. **Primary LLM**: Claude Agent SDK for all agent sessions (Planner, Coder, QA)
2. **Memory System**: Graphiti + LadybugDB for cross-session learning, with file-based fallback

### Key Principles

- **Claude Agent SDK** handles all agent interactions (NOT direct Anthropic API)
- **OAuth authentication** via `claude setup-token` (NOT API keys for agents)
- **Memory LLM/Embeddings** are separate and configurable (6 providers each)
- **Offline capable** via Ollama for fully local operation

---

## 2. Current Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     CLAUDE AGENT SDK (OAuth)                         │
│  Primary LLM for all agent sessions                                  │
│  Model: claude-opus-4-5-20251101 (configurable via AUTO_BUILD_MODEL)│
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         AGENT SESSIONS                               │
│  ┌──────────┐  ┌──────────┐  ┌────────────┐  ┌──────────┐          │
│  │ Planner  │  │  Coder   │  │ QA Reviewer│  │ QA Fixer │          │
│  └──────────┘  └──────────┘  └────────────┘  └──────────┘          │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         MEMORY SYSTEM                                │
│                                                                      │
│   ┌─────────────────────────────┐   ┌────────────────────────────┐ │
│   │  PRIMARY: Graphiti          │   │  FALLBACK: File-based     │ │
│   │  + LadybugDB (embedded)     │   │  (always available)        │ │
│   │                             │   │                            │ │
│   │  LLM Provider (6 options):  │   │  Storage:                  │ │
│   │  - OpenAI                   │   │  - session_insights/*.json │ │
│   │  - Anthropic                │   │  - patterns.md             │ │
│   │  - Ollama (offline)         │   │  - gotchas.md              │ │
│   │  - Google AI                │   │  - codebase_map.json       │ │
│   │  - Azure OpenAI             │   │                            │ │
│   │  - OpenRouter               │   │                            │ │
│   │                             │   │                            │ │
│   │  Embedder Provider:         │   │                            │ │
│   │  (same 6 options)           │   │                            │ │
│   └─────────────────────────────┘   └────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Claude Agent SDK (Primary LLM)

The Claude Agent SDK is the **primary LLM** for all agent interactions.

### Authentication

```bash
# Setup OAuth token (NOT API key)
claude setup-token

# Token is stored and used automatically
# Environment variable: CLAUDE_CODE_OAUTH_TOKEN
```

### Configuration

| Setting | Environment Variable | Default |
|---------|---------------------|---------|
| Model | `AUTO_BUILD_MODEL` | `claude-opus-4-5-20251101` |
| Thinking tokens | `MAX_THINKING_TOKENS` | None (unlimited) |
| Agent type | Per-session | planner, coder, qa_reviewer, qa_fixer |

### Key File

```
apps/backend/core/client.py
```

**Usage in agents:**
```python
from core.client import create_client

client = create_client(
    project_dir=project_dir,
    spec_dir=spec_dir,
    model="claude-opus-4-5-20251101",
    agent_type="coder",
    max_thinking_tokens=None
)
```

---

## 4. Memory System

### Dual-Layer Architecture

| Layer | Technology | Purpose | Availability |
|-------|------------|---------|--------------|
| **Primary** | Graphiti + LadybugDB | Semantic search, knowledge graph | When `GRAPHITI_ENABLED=true` |
| **Fallback** | File-based (JSON/MD) | Human-readable, zero dependencies | Always available |

### Memory Manager

```python
# apps/backend/agents/memory_manager.py

# Get context before starting subtask
context = await get_graphiti_context(spec_dir, project_dir, subtask)

# Save learnings after session
success, storage_type = await save_session_memory(
    spec_dir, project_dir, subtask_id, session_num,
    success, subtasks_completed, discoveries
)
```

### Episode Types

| Type | Purpose | Example |
|------|---------|---------|
| `SESSION_INSIGHT` | What was learned | "React components should use hooks" |
| `CODEBASE_DISCOVERY` | File purposes | "auth.py handles JWT validation" |
| `PATTERN` | Successful patterns | "Use async/await for API calls" |
| `GOTCHA` | Pitfalls to avoid | "Don't use mutable default args" |
| `TASK_OUTCOME` | Subtask results | "Subtask 1.2 completed successfully" |
| `QA_RESULT` | Validation results | "All tests passed" |

---

## 5. LLM Providers for Memory

The memory system uses a **separate LLM** for processing insights and generating context. This is **independent** of the Claude Agent SDK.

### Available Providers

| Provider | Default Model | API Key Variable | Notes |
|----------|---------------|------------------|-------|
| **OpenAI** | `gpt-5-mini` | `OPENAI_API_KEY` | Simplest setup |
| **Anthropic** | `claude-sonnet-4-5` | `ANTHROPIC_API_KEY` | Pair with Voyage for embeddings |
| **Ollama** | `deepseek-r1:7b` | (none - local) | Fully offline |
| **Google AI** | `gemini-2.0-flash` | `GOOGLE_API_KEY` | Gemini ecosystem |
| **Azure OpenAI** | Configurable | `AZURE_OPENAI_API_KEY` | Enterprise deployments |
| **OpenRouter** | Multi-provider | `OPENROUTER_API_KEY` | Aggregates multiple providers |

### Configuration

```bash
# Select LLM provider
GRAPHITI_LLM_PROVIDER=openai  # or anthropic, ollama, google, azure_openai, openrouter

# Provider-specific settings
OPENAI_API_KEY=sk-xxxxxxxx
OPENAI_MODEL=gpt-5-mini
```

### Source Files

```
apps/backend/integrations/graphiti/providers_pkg/llm_providers/
├── openai_llm.py
├── anthropic_llm.py
├── ollama_llm.py
├── google_llm.py
├── azure_openai_llm.py
└── openrouter_llm.py
```

---

## 6. Embedder Providers

Embeddings power **semantic search** in the knowledge graph, enabling context retrieval based on meaning rather than keywords.

### Available Providers

| Provider | Default Model | Dimensions | API Key Variable |
|----------|---------------|------------|------------------|
| **OpenAI** | `text-embedding-3-small` | 1536 | `OPENAI_API_KEY` |
| **Voyage AI** | `voyage-3` | 1024 | `VOYAGE_API_KEY` |
| **Ollama** | `nomic-embed-text` | 768 | (none - local) |
| **Google AI** | `text-embedding-004` | 768 | `GOOGLE_API_KEY` |
| **Azure OpenAI** | Configurable | 1536 | `AZURE_OPENAI_API_KEY` |
| **OpenRouter** | `text-embedding-3-small` | 1536 | `OPENROUTER_API_KEY` |

### Embedding Dimensions Reference

```python
EMBEDDING_DIMENSIONS = {
    # OpenAI
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,

    # Voyage AI
    "voyage-3": 1024,
    "voyage-3-lite": 512,
    "voyage-large-2": 1536,

    # Ollama
    "nomic-embed-text": 768,
    "mxbai-embed-large": 1024,
    "all-minilm": 384,
    "snowflake-arctic-embed": 1024,

    # Google AI
    "text-embedding-004": 768,
}
```

### Configuration

```bash
# Select embedder provider
GRAPHITI_EMBEDDER_PROVIDER=openai  # or voyage, ollama, google, azure_openai, openrouter

# Provider-specific settings
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

### Source Files

```
apps/backend/integrations/graphiti/providers_pkg/embedder_providers/
├── openai_embedder.py
├── voyage_embedder.py
├── ollama_embedder.py
├── google_embedder.py
├── azure_openai_embedder.py
└── openrouter_embedder.py
```

---

## 7. Offline/Local Setup (Ollama)

For fully offline operation without internet connectivity.

### Prerequisites

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull models
ollama pull deepseek-r1:7b      # LLM
ollama pull nomic-embed-text    # Embeddings
```

### Available Offline Models

**LLM Models:**
| Model | Size | Use Case |
|-------|------|----------|
| `deepseek-r1:7b` | 4GB | Reasoning, code |
| `llama3:8b` | 4.7GB | General purpose |
| `mistral:7b` | 4.1GB | Fast, efficient |
| `codellama:7b` | 3.8GB | Code-focused |
| `qwen2.5:7b` | 4.4GB | Multilingual |

**Embedding Models:**
| Model | Dimensions | Notes |
|-------|------------|-------|
| `nomic-embed-text` | 768 | Recommended default |
| `mxbai-embed-large` | 1024 | Higher quality |
| `all-minilm` | 384 | Fast, lightweight |
| `snowflake-arctic-embed` | 1024 | High performance |

### Configuration

```bash
# apps/backend/.env

GRAPHITI_ENABLED=true
GRAPHITI_LLM_PROVIDER=ollama
GRAPHITI_EMBEDDER_PROVIDER=ollama

# Ollama settings
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_LLM_MODEL=deepseek-r1:7b
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
OLLAMA_EMBEDDING_DIM=768
```

### Advantages

- No internet required after initial model download
- No API costs
- Data stays local (privacy)
- Works air-gapped

### Limitations

- Requires GPU for reasonable speed (CPU works but slow)
- Model quality varies vs cloud providers
- Initial model download requires internet

---

## 8. Configuration Examples

### Example 1: OpenAI (Simplest)

```bash
# apps/backend/.env

GRAPHITI_ENABLED=true
GRAPHITI_LLM_PROVIDER=openai
GRAPHITI_EMBEDDER_PROVIDER=openai

OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_MODEL=gpt-5-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

### Example 2: Anthropic + Voyage (High Quality)

```bash
# apps/backend/.env

GRAPHITI_ENABLED=true
GRAPHITI_LLM_PROVIDER=anthropic
GRAPHITI_EMBEDDER_PROVIDER=voyage

ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GRAPHITI_ANTHROPIC_MODEL=claude-sonnet-4-5-latest

VOYAGE_API_KEY=pa-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
VOYAGE_EMBEDDING_MODEL=voyage-3
```

### Example 3: Ollama (Fully Offline)

```bash
# apps/backend/.env

GRAPHITI_ENABLED=true
GRAPHITI_LLM_PROVIDER=ollama
GRAPHITI_EMBEDDER_PROVIDER=ollama

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_LLM_MODEL=deepseek-r1:7b
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
OLLAMA_EMBEDDING_DIM=768
```

### Example 4: Azure OpenAI (Enterprise)

```bash
# apps/backend/.env

GRAPHITI_ENABLED=true
GRAPHITI_LLM_PROVIDER=azure_openai
GRAPHITI_EMBEDDER_PROVIDER=azure_openai

AZURE_OPENAI_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
AZURE_OPENAI_BASE_URL=https://your-resource.openai.azure.com/openai/deployments
AZURE_OPENAI_LLM_DEPLOYMENT=gpt-4
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-small
```

### Example 5: Google AI (Gemini)

```bash
# apps/backend/.env

GRAPHITI_ENABLED=true
GRAPHITI_LLM_PROVIDER=google
GRAPHITI_EMBEDDER_PROVIDER=google

GOOGLE_API_KEY=AIzaSyxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GOOGLE_LLM_MODEL=gemini-2.0-flash
GOOGLE_EMBEDDING_MODEL=text-embedding-004
```

### Example 6: OpenRouter (Multi-Provider)

```bash
# apps/backend/.env

GRAPHITI_ENABLED=true
GRAPHITI_LLM_PROVIDER=openrouter
GRAPHITI_EMBEDDER_PROVIDER=openrouter

OPENROUTER_API_KEY=sk-or-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_LLM_MODEL=anthropic/claude-3.5-sonnet
OPENROUTER_EMBEDDING_MODEL=openai/text-embedding-3-small
```

---

## 9. Memory Storage Structure

### Per-Spec Memory Directory

```
.magestic-ai/specs/001-feature-name/
├── spec.md                         # Feature specification
├── implementation_plan.json        # Subtask plan
├── memory/                         # File-based memory (fallback)
│   ├── codebase_map.json          # Discovered file purposes
│   ├── patterns.md                # Successful patterns
│   ├── gotchas.md                 # Pitfalls to avoid
│   └── session_insights/
│       ├── session_001.json       # Session 1 learnings
│       └── session_002.json       # Session 2 learnings
└── graphiti/                       # Graphiti database (if enabled)
    └── [LadybugDB files]          # Graph database storage
```

### Global Memory Location

```
~/.magestic-ai/memories/           # Shared across projects (if configured)
```

---

## 10. Key Source Files

| File | Purpose |
|------|---------|
| `apps/backend/core/client.py` | Claude Agent SDK client factory |
| `apps/backend/integrations/graphiti/config.py` | Memory provider configuration |
| `apps/backend/integrations/graphiti/providers_pkg/factory.py` | Provider factory |
| `apps/backend/integrations/graphiti/queries_pkg/graphiti.py` | GraphitiMemory class |
| `apps/backend/integrations/graphiti/queries_pkg/client.py` | LadybugDB client |
| `apps/backend/integrations/graphiti/queries_pkg/search.py` | Semantic search |
| `apps/backend/agents/memory_manager.py` | Dual-layer memory orchestrator |
| `apps/backend/memory/` | File-based memory fallback |
| `apps/backend/.env.example` | Environment variable reference |

---

## Summary

| Component | Technology | Configuration |
|-----------|------------|---------------|
| **Agent LLM** | Claude Agent SDK | OAuth token via `claude setup-token` |
| **Memory LLM** | 6 providers | `GRAPHITI_LLM_PROVIDER` |
| **Embeddings** | 6 providers | `GRAPHITI_EMBEDDER_PROVIDER` |
| **Database** | LadybugDB (embedded) | No Docker required |
| **Fallback** | File-based | Always available |
| **Offline** | Ollama | Full local operation |

---

*Created: 2026-01-07*
