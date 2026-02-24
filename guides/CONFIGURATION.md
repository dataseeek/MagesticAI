# Claude Code Manager Web - Configuration Guide

This comprehensive guide covers all environment variables, configuration files, and customization options for Claude Code Manager Web. It includes settings for development, production, and enterprise deployments.

---

## Table of Contents

1. [Configuration Overview](#configuration-overview)
2. [Configuration File Locations](#configuration-file-locations)
3. [Backend Configuration (apps/backend/.env)](#backend-configuration-appsbackendenv)
4. [Web Server Configuration (apps/web-server/.env)](#web-server-configuration-appsweb-serverenv)
5. [Application Settings (settings.json)](#application-settings-settingsjson)
6. [Graphiti Memory System](#graphiti-memory-system)
7. [Integration Configuration](#integration-configuration)
8. [Security Configuration](#security-configuration)
9. [Production Configuration](#production-configuration)
10. [Development vs Production](#development-vs-production)
11. [Customization Options](#customization-options)
12. [Environment Variable Reference](#environment-variable-reference)

---

## Configuration Overview

Claude Code Manager Web uses a layered configuration system:

```
Configuration Hierarchy
├── Environment Variables (.env files)
│   ├── apps/backend/.env         # AI agent configuration
│   └── apps/web-server/.env      # API server configuration
├── Application Settings
│   └── ~/.auto-claude-web/settings.json
├── Project-Level Settings
│   └── .auto-claude/ (per project)
└── Runtime Settings
    └── Web UI Settings Panel
```

### Configuration Precedence

1. **Environment variables** - Highest priority, set in `.env` files or system environment
2. **Application settings** - User preferences stored in `settings.json`
3. **Default values** - Built-in defaults used when no configuration is provided

---

## Configuration File Locations

### System-Wide Files

| File | Location | Purpose |
|------|----------|---------|
| **API Token** | `~/.auto-claude-web/.token` | Authentication token for API access |
| **Settings** | `~/.auto-claude-web/settings.json` | Application preferences |
| **SSL Certificates** | `~/.auto-claude-web/ssl/` | HTTPS certificates (when enabled) |
| **Claude Profiles** | `~/.auto-claude-web/claude-profiles.json` | Saved Claude profiles |
| **Tab State** | `~/.auto-claude-web/tab-state.json` | UI state persistence |
| **Memory Database** | `~/.auto-claude/memories/` | Graphiti memory storage |

### Application Files

| File | Location | Purpose |
|------|----------|---------|
| **Backend .env** | `apps/backend/.env` | AI agent configuration |
| **Web Server .env** | `apps/web-server/.env` | API server settings |
| **Example Configs** | `apps/*/.env.example` | Template configurations |

### Project Files (Per Repository)

| File | Location | Purpose |
|------|----------|---------|
| **Specs** | `.auto-claude/specs/` | Task specifications |
| **Worktrees** | `.auto-claude/worktrees/` | Isolated task branches |
| **Project Index** | `.auto-claude/project_index.json` | Codebase indexing data |
| **Roadmap** | `.auto-claude/roadmap/` | Generated roadmaps |
| **Ideation** | `.auto-claude/ideation/` | Feature ideas |

---

## Backend Configuration (apps/backend/.env)

The backend `.env` file configures AI agents, memory systems, and integrations.

### Creating the Configuration

```bash
# Copy the example file
cp apps/backend/.env.example apps/backend/.env

# Edit with your preferred editor
nano apps/backend/.env
```

### Authentication (Required)

```bash
# =============================================================================
# AUTHENTICATION (REQUIRED)
# =============================================================================

# Option 1: OAuth Token (Recommended)
# Run `claude setup-token` to obtain from Claude Code CLI
CLAUDE_CODE_OAUTH_TOKEN=your-oauth-token-here

# Option 2: Enterprise/Proxy Authentication (CCR)
# ANTHROPIC_AUTH_TOKEN=sk-zcf-x-ccr
```

> **Important:** Direct API keys (`ANTHROPIC_API_KEY`) are NOT supported to prevent silent billing. Always use OAuth tokens.

### Custom API Endpoint (Optional)

```bash
# =============================================================================
# CUSTOM API ENDPOINT (OPTIONAL)
# =============================================================================

# Override default Anthropic endpoint for:
#   - Local proxies (ccr, litellm)
#   - API gateways
#   - Self-hosted instances
ANTHROPIC_BASE_URL=http://127.0.0.1:3456

# Related settings (usually set together)
NO_PROXY=127.0.0.1
DISABLE_TELEMETRY=true
DISABLE_COST_WARNINGS=true
API_TIMEOUT_MS=600000
```

### Model Configuration

```bash
# =============================================================================
# MODEL CONFIGURATION
# =============================================================================

# Default model for agents (optional)
# Default: claude-opus-4-5-20251101
AUTO_BUILD_MODEL=claude-opus-4-5-20251101
```

### Git/Worktree Settings

```bash
# =============================================================================
# GIT/WORKTREE SETTINGS
# =============================================================================

# Default base branch for worktree creation
# If not set, auto-detects main/master or uses current branch
DEFAULT_BRANCH=main
```

### Debug Mode

```bash
# =============================================================================
# DEBUG MODE
# =============================================================================

# Enable debug logging (default: false)
DEBUG=true

# Debug log level: 1=basic, 2=detailed, 3=verbose
DEBUG_LEVEL=1

# Log to file instead of stdout
DEBUG_LOG_FILE=auto-claude/debug.log
```

### UI Settings

```bash
# =============================================================================
# UI SETTINGS
# =============================================================================

# Enable fancy terminal UI with icons and colors
# Set to "false" for CI/CD or log files
ENABLE_FANCY_UI=true
```

---

## Web Server Configuration (apps/web-server/.env)

The web server `.env` file configures the FastAPI backend server.

### Creating the Configuration

```bash
cp apps/web-server/.env.example apps/web-server/.env
nano apps/web-server/.env
```

### Server Settings

```bash
# =============================================================================
# SERVER SETTINGS
# =============================================================================

# Bind address (0.0.0.0 allows remote access)
APP_HOST=0.0.0.0

# Server port
APP_PORT=8000

# Enable debug mode
APP_DEBUG=true
```

### Authentication

```bash
# =============================================================================
# AUTHENTICATION
# =============================================================================

# API token - auto-generated if not set
# APP_API_TOKEN=your-secure-token-here
```

The API token is automatically generated on first run and saved to `~/.auto-claude-web/.token`.

### SSL/HTTPS Configuration

```bash
# =============================================================================
# SSL CONFIGURATION
# =============================================================================

# Enable HTTPS
APP_SSL_ENABLED=false

# Custom certificate paths (optional)
# If not provided, self-signed certificates are generated
APP_SSL_CERTFILE=/path/to/cert.pem
APP_SSL_KEYFILE=/path/to/key.pem
```

### CORS Settings

```bash
# =============================================================================
# CORS CONFIGURATION
# =============================================================================

# Allowed origins (JSON array format)
APP_CORS_ORIGINS=["http://localhost:5173", "http://localhost:3000"]
```

### Terminal Settings

```bash
# =============================================================================
# TERMINAL SETTINGS
# =============================================================================

# Default shell for terminals
APP_DEFAULT_SHELL=/bin/bash

# Maximum concurrent terminals
APP_MAX_TERMINALS=20
```

### Task Execution

```bash
# =============================================================================
# TASK EXECUTION
# =============================================================================

# Maximum concurrent AI tasks
APP_MAX_CONCURRENT_TASKS=5
```

### Path Configuration

```bash
# =============================================================================
# PATHS (Auto-detected if not set)
# =============================================================================

# Path to backend agents
APP_BACKEND_PATH=/path/to/apps/backend

# Directory for project data storage
APP_PROJECTS_DATA_DIR=/path/to/data/directory
```

---

## Application Settings (settings.json)

Application settings are stored in `~/.auto-claude-web/settings.json` and can be modified through the Settings panel in the web UI.

### General Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `theme` | string | `"system"` | UI theme: `"light"`, `"dark"`, or `"system"` |
| `colorTheme` | string | `"default"` | Color scheme: `default`, `dusk`, `lime`, `ocean`, `retro`, `neo`, `forest` |
| `language` | string | `"en"` | UI language (en, fr, pt-BR) |
| `uiScale` | number | `100` | UI scale percentage (75-200) |

### Claude Configuration

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `defaultModel` | string | `"claude-sonnet-4-5-20250929"` | Default Claude model |
| `selectedAgentProfile` | string | `"auto"` | Agent profile for model/thinking configuration |
| `thinkingLevel` | string | `"extended"` | Thinking level: `none`, `standard`, `extended` |

### Task Execution

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `autoContinue` | boolean | `true` | Auto-continue to next phase after spec creation |
| `autoQa` | boolean | `true` | Automatically run QA after implementation |

### Terminal Configuration

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `defaultShell` | string | `"/bin/bash"` | Default shell for terminals |
| `terminalFontSize` | number | `14` | Terminal font size |
| `autoNameTerminals` | boolean | `true` | Auto-generate terminal names |

### Integration Toggles

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `githubEnabled` | boolean | `false` | Enable GitHub integration |
| `gitlabEnabled` | boolean | `false` | Enable GitLab integration |
| `linearEnabled` | boolean | `false` | Enable Linear integration |
| `graphitiEnabled` | boolean | `true` | Enable Graphiti memory |

### Developer Tools

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `preferredIDE` | string | `undefined` | Preferred code editor |
| `customIDEPath` | string | `undefined` | Custom IDE executable path |
| `preferredTerminal` | string | `undefined` | Preferred terminal emulator |
| `customTerminalPath` | string | `undefined` | Custom terminal path |

### Notification Settings

```json
{
  "notifications": {
    "onTaskComplete": true,
    "onTaskFailed": true,
    "onReviewNeeded": true,
    "sound": false
  }
}
```

---

## Graphiti Memory System

Graphiti provides persistent memory for cross-session context retention using LadybugDB as the embedded graph database.

### Enabling Graphiti

```bash
# Required: Enable Graphiti
GRAPHITI_ENABLED=true
```

### Database Settings

```bash
# Database name (default: auto_claude_memory)
GRAPHITI_DATABASE=auto_claude_memory

# Storage path (default: ~/.auto-claude/memories)
GRAPHITI_DB_PATH=~/.auto-claude/memories
```

### Provider Selection

Graphiti supports multiple LLM and embedding providers:

```bash
# LLM provider: openai | anthropic | azure_openai | ollama | google | openrouter
GRAPHITI_LLM_PROVIDER=openai

# Embedder provider: openai | voyage | azure_openai | ollama | google | openrouter
GRAPHITI_EMBEDDER_PROVIDER=openai
```

### Provider Configurations

#### OpenAI (Default)

```bash
GRAPHITI_LLM_PROVIDER=openai
GRAPHITI_EMBEDDER_PROVIDER=openai
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

#### Anthropic + Voyage (High Quality)

```bash
GRAPHITI_LLM_PROVIDER=anthropic
GRAPHITI_EMBEDDER_PROVIDER=voyage
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GRAPHITI_ANTHROPIC_MODEL=claude-sonnet-4-5-latest
VOYAGE_API_KEY=pa-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
VOYAGE_EMBEDDING_MODEL=voyage-3
```

#### Google AI (Gemini)

```bash
GRAPHITI_LLM_PROVIDER=google
GRAPHITI_EMBEDDER_PROVIDER=google
GOOGLE_API_KEY=AIzaSyxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GOOGLE_LLM_MODEL=gemini-2.0-flash
GOOGLE_EMBEDDING_MODEL=text-embedding-004
```

#### Ollama (Fully Offline)

```bash
GRAPHITI_LLM_PROVIDER=ollama
GRAPHITI_EMBEDDER_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_LLM_MODEL=deepseek-r1:7b
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
OLLAMA_EMBEDDING_DIM=768
```

**Supported Ollama embedding models:**
| Model | Dimensions |
|-------|------------|
| `nomic-embed-text` | 768 |
| `embeddinggemma` | 768 |
| `mxbai-embed-large` | 1024 |
| `bge-large` | 1024 |
| `qwen3-embedding:0.6b` | 1024 |
| `qwen3-embedding:4b` | 2560 |
| `qwen3-embedding:8b` | 4096 |

#### Azure OpenAI (Enterprise)

```bash
GRAPHITI_LLM_PROVIDER=azure_openai
GRAPHITI_EMBEDDER_PROVIDER=azure_openai
AZURE_OPENAI_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
AZURE_OPENAI_BASE_URL=https://your-resource.openai.azure.com/openai/deployments/your-deployment
AZURE_OPENAI_LLM_DEPLOYMENT=gpt-4
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-small
```

#### OpenRouter (Multi-Provider)

```bash
GRAPHITI_LLM_PROVIDER=openrouter
GRAPHITI_EMBEDDER_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_LLM_MODEL=anthropic/claude-3.5-sonnet
OPENROUTER_EMBEDDING_MODEL=openai/text-embedding-3-small
```

---

## Integration Configuration

### GitHub Integration

```bash
# GitHub Personal Access Token
# Required scopes: repo, read:org
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Or authenticate via CLI:
```bash
gh auth login
```

### GitLab Integration

```bash
# GitLab Instance URL (default: gitlab.com)
GITLAB_INSTANCE_URL=https://gitlab.com

# GitLab Personal Access Token
# Required scope: api
GITLAB_TOKEN=glpat-xxxxxxxxxxxxxxxxxxxx

# GitLab Project (optional - auto-detected from git remote)
GITLAB_PROJECT=mygroup/myproject
```

Or authenticate via CLI:
```bash
glab auth login
```

### Linear Integration

```bash
# Linear API Key
# Get from: https://linear.app/YOUR-TEAM/settings/api
LINEAR_API_KEY=lin_api_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Pre-configured IDs (optional - auto-detected)
LINEAR_TEAM_ID=
LINEAR_PROJECT_ID=
```

---

## Security Configuration

### File Permissions

All sensitive configuration files are automatically set to secure permissions:

| File | Permissions | Purpose |
|------|-------------|---------|
| `~/.auto-claude-web/.token` | `0o600` | API authentication token |
| `~/.auto-claude-web/claude-profiles.json` | `0o600` | OAuth tokens |
| `~/.auto-claude-web/api-profiles.json` | `0o600` | API keys |
| `apps/backend/.env` | `0o600` | Environment secrets |
| `~/.auto-claude-web/ssl/*.pem` | `0o600` | SSL certificates |

### API Token Security

- Tokens are auto-generated using `secrets.token_urlsafe(32)`
- Stored with owner-only read/write permissions
- Required for all API requests (`Authorization: Bearer <token>`)

### SSL/HTTPS Setup

For production deployments, enable HTTPS:

```bash
# Enable SSL
APP_SSL_ENABLED=true

# Use custom certificates (recommended for production)
APP_SSL_CERTFILE=/etc/ssl/certs/your-cert.pem
APP_SSL_KEYFILE=/etc/ssl/private/your-key.pem
```

Self-signed certificates are automatically generated if custom paths aren't provided.

### Environment Variable Security

**Never commit `.env` files to version control!**

```bash
# Add to .gitignore
echo "*.env" >> .gitignore
echo ".env.*" >> .gitignore
```

---

## Production Configuration

### Recommended Production Settings

#### Web Server (apps/web-server/.env)

```bash
# Production server settings
APP_HOST=0.0.0.0
APP_PORT=8000
APP_DEBUG=false

# Enable HTTPS
APP_SSL_ENABLED=true
APP_SSL_CERTFILE=/etc/ssl/certs/production.pem
APP_SSL_KEYFILE=/etc/ssl/private/production-key.pem

# Restricted CORS origins
APP_CORS_ORIGINS=["https://your-domain.com"]

# Resource limits
APP_MAX_TERMINALS=50
APP_MAX_CONCURRENT_TASKS=10
```

#### Backend (apps/backend/.env)

```bash
# Production backend settings
DEBUG=false
ENABLE_FANCY_UI=false

# Graphiti with high-quality provider
GRAPHITI_ENABLED=true
GRAPHITI_LLM_PROVIDER=anthropic
GRAPHITI_EMBEDDER_PROVIDER=voyage

# Disable telemetry
DISABLE_TELEMETRY=true
```

### Reverse Proxy Configuration

Example Nginx configuration:

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/ssl/certs/production.pem;
    ssl_certificate_key /etc/ssl/private/production-key.pem;

    # WebSocket support
    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }

    # API endpoints
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Frontend
    location / {
        proxy_pass http://localhost:5173;
        proxy_set_header Host $host;
    }
}
```

---

## Development vs Production

### Key Differences

| Setting | Development | Production |
|---------|-------------|------------|
| `DEBUG` | `true` | `false` |
| `APP_DEBUG` | `true` | `false` |
| `SSL_ENABLED` | `false` | `true` |
| `CORS_ORIGINS` | `localhost:*` | Specific domains |
| `MAX_CONCURRENT_TASKS` | `5` | `10+` |
| `ENABLE_FANCY_UI` | `true` | `false` |
| `LOG_LEVEL` | `1-3` | `1` |

### Development Quick Start

```bash
# Backend .env
DEBUG=true
CLAUDE_CODE_OAUTH_TOKEN=your-token
GRAPHITI_ENABLED=true

# Web Server .env
APP_DEBUG=true
APP_HOST=127.0.0.1
APP_PORT=8000
```

### Production Checklist

- [ ] Set `DEBUG=false` in all `.env` files
- [ ] Enable SSL/HTTPS
- [ ] Configure proper CORS origins
- [ ] Use secure, rotated API tokens
- [ ] Set up log rotation
- [ ] Configure reverse proxy
- [ ] Set file permissions correctly
- [ ] Remove development dependencies
- [ ] Enable rate limiting
- [ ] Set up monitoring

---

## Customization Options

### Theme Customization

Available color themes in `settings.json`:

| Theme | Description |
|-------|-------------|
| `default` | Standard dark/light theme |
| `dusk` | Purple-tinted evening theme |
| `lime` | Green-accented theme |
| `ocean` | Blue-tinted theme |
| `retro` | Vintage-inspired colors |
| `neo` | Modern neon accents |
| `forest` | Nature-inspired greens |

### Agent Profiles

Configure AI behavior per phase:

```json
{
  "selectedAgentProfile": "auto",
  "customPhaseModels": {
    "spec": "sonnet",
    "planning": "opus",
    "coding": "opus",
    "qa": "sonnet"
  },
  "customPhaseThinking": {
    "spec": "medium",
    "planning": "high",
    "coding": "high",
    "qa": "medium"
  }
}
```

### Model Selection

Available models:
- `haiku` - Fast, efficient for simple tasks
- `sonnet` - Balanced performance and quality
- `opus` - Highest quality for complex tasks

### Thinking Levels

| Level | Description |
|-------|-------------|
| `none` | No extended thinking |
| `low` | Minimal thinking budget |
| `medium` | Balanced thinking |
| `high` | Extended thinking |
| `ultrathink` | Maximum thinking budget |

---

## Environment Variable Reference

### Complete Backend Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CLAUDE_CODE_OAUTH_TOKEN` | Yes* | - | OAuth token for Claude |
| `ANTHROPIC_AUTH_TOKEN` | Yes* | - | Enterprise auth token (CCR) |
| `ANTHROPIC_BASE_URL` | No | - | Custom API endpoint |
| `AUTO_BUILD_MODEL` | No | `claude-opus-4-5-20251101` | Default model |
| `DEFAULT_BRANCH` | No | Auto-detect | Base branch for worktrees |
| `DEBUG` | No | `false` | Enable debug mode |
| `DEBUG_LEVEL` | No | `1` | Debug verbosity (1-3) |
| `DEBUG_LOG_FILE` | No | - | Log file path |
| `ENABLE_FANCY_UI` | No | `true` | Terminal UI enhancements |
| `GRAPHITI_ENABLED` | No | `true` | Enable memory system |
| `GRAPHITI_DATABASE` | No | `auto_claude_memory` | Database name |
| `GRAPHITI_DB_PATH` | No | `~/.auto-claude/memories` | Storage path |
| `GRAPHITI_LLM_PROVIDER` | No | `openai` | LLM provider |
| `GRAPHITI_EMBEDDER_PROVIDER` | No | `openai` | Embedding provider |
| `LINEAR_API_KEY` | No | - | Linear integration |
| `GITHUB_TOKEN` | No | - | GitHub integration |
| `GITLAB_TOKEN` | No | - | GitLab integration |
| `GITLAB_INSTANCE_URL` | No | `https://gitlab.com` | GitLab URL |

*One authentication method required

### Complete Web Server Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `APP_HOST` | No | `0.0.0.0` | Server bind address |
| `APP_PORT` | No | `8000` | Server port |
| `APP_DEBUG` | No | `false` | Debug mode |
| `APP_API_TOKEN` | No | Auto-generated | API token |
| `APP_CORS_ORIGINS` | No | `localhost:*` | CORS origins |
| `APP_SSL_ENABLED` | No | `false` | Enable HTTPS |
| `APP_SSL_CERTFILE` | No | Auto-generated | SSL certificate |
| `APP_SSL_KEYFILE` | No | Auto-generated | SSL private key |
| `APP_DEFAULT_SHELL` | No | `/bin/bash` | Default shell |
| `APP_MAX_TERMINALS` | No | `20` | Max terminals |
| `APP_MAX_CONCURRENT_TASKS` | No | `5` | Max concurrent tasks |
| `APP_BACKEND_PATH` | No | Auto-detect | Backend path |
| `APP_PROJECTS_DATA_DIR` | No | `~/.auto-claude-web` | Data directory |

---

## Related Guides

- **[Getting Started](GETTING-STARTED.md)** - Initial setup and first-run configuration
- **[Development Setup](DEVELOPMENT-SETUP.md)** - Development environment configuration
- **[Architecture](ARCHITECTURE.md)** - System design and configuration architecture
- **[Troubleshooting](TROUBLESHOOTING.md)** - Common configuration issues and solutions

---

## Get Help

- **GitHub Issues:** [Report configuration problems](https://github.com/dataseeek/Claude-Code-Manager-Web/issues)
- **GitHub Discussions:** [Ask configuration questions](https://github.com/dataseeek/Claude-Code-Manager-Web/discussions)

---

**Claude Code Manager Web** - Comprehensive configuration for every deployment scenario!
