# =============================================================================
# MagesticAI - Multi-Stage Docker Build
# =============================================================================
# Stage 1: Build React frontend
# Stage 2: Ubuntu runtime with Python backend + built frontend
# =============================================================================

# Global ARG — must be declared before any FROM that uses it
# Ubuntu 24.04 LTS ships Python 3.12 natively.
# For 22.04, you'd need: add-apt-repository ppa:deadsnakes/ppa && apt install python3.12
ARG UBUNTU_VERSION=24.04

# ---------------------------------------------------------------------------
# Stage 1: Build frontend (React 19 + Vite)
# ---------------------------------------------------------------------------
FROM node:24-bookworm AS frontend-build

WORKDIR /build

# Copy root package files first for layer caching (npm workspaces)
COPY package.json package-lock.json ./

# Copy only the frontend workspace package.json for dependency resolution
COPY apps/frontend-web/package.json apps/frontend-web/

# Install dependencies (workspace-aware)
RUN npm ci --workspace=apps/frontend-web

# Copy frontend source
COPY apps/frontend-web/ apps/frontend-web/

# Build → outputs to apps/web-server/static/
# (vite.config.ts: build.outDir = '../web-server/static')
RUN mkdir -p apps/web-server/static && \
    cd apps/frontend-web && npm run build

# ---------------------------------------------------------------------------
# Stage 2: Runtime (Ubuntu + Python)
# ---------------------------------------------------------------------------
FROM ubuntu:${UBUNTU_VERSION} AS runtime

ENV DEBIAN_FRONTEND=noninteractive

# System packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-venv \
    python3-pip \
    python3-dev \
    git \
    curl \
    unzip \
    ca-certificates \
    build-essential \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user with tty group (needed for PTY terminal access)
RUN useradd -m -s /bin/bash -G tty magesticai

# Project directory (matches the plan: /home/projects/MagesticAI)
RUN mkdir -p /home/projects/MagesticAI && \
    chown -R magesticai:magesticai /home/projects

# Copy project files
COPY --chown=magesticai:magesticai . /home/projects/MagesticAI/

# Copy built frontend from Stage 1
COPY --from=frontend-build --chown=magesticai:magesticai \
    /build/apps/web-server/static/ \
    /home/projects/MagesticAI/apps/web-server/static/

# Copy Node.js from the frontend build stage so it's available at runtime
# (needed for npm install -g @anthropic-ai/claude-code)
COPY --from=frontend-build /usr/local/bin/node /usr/local/bin/node
COPY --from=frontend-build /usr/local/lib/node_modules/ /usr/local/lib/node_modules/
RUN ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm && \
    ln -s ../lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx

# Switch to non-root user for remaining setup
USER magesticai

# Configure npm global installs to go to user-writable directory
# (non-root user can't write to /usr/local/lib/node_modules)
RUN mkdir -p /home/magesticai/.npm-global && \
    npm config set prefix /home/magesticai/.npm-global

# Create single Python venv (both web-server and backend share it,
# because agent_service.py spawns backend scripts via sys.executable)
RUN python3 -m venv /home/projects/MagesticAI/.venv

# Install both requirements into the same venv
RUN /home/projects/MagesticAI/.venv/bin/pip install --no-cache-dir \
    -r /home/projects/MagesticAI/apps/web-server/requirements.txt \
    -r /home/projects/MagesticAI/apps/backend/requirements.txt

# Git config (required for worktree operations inside the container)
RUN git config --global user.name "MagesticAI" && \
    git config --global user.email "magesticai@container"

# Create data directory for persistent state
RUN mkdir -p /home/magesticai/.magestic-ai

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
ENV APP_HOST=0.0.0.0 \
    APP_PORT=8000 \
    APP_BACKEND_PATH=/home/projects/MagesticAI/apps/backend \
    APP_PROJECTS_DATA_DIR=/home/magesticai/.magestic-ai \
    APP_DEFAULT_SHELL=/bin/bash \
    PYTHONUNBUFFERED=1 \
    # npm global bin + venv Python on PATH
    PATH="/home/magesticai/.npm-global/bin:/home/projects/MagesticAI/.venv/bin:$PATH"

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

WORKDIR /home/projects/MagesticAI/apps/web-server

CMD ["python", "-m", "server.main"]
