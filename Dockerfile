# =============================================================================
# Martinica - Multi-Stage Docker Build
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
    ca-certificates \
    build-essential \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user with tty group (needed for PTY terminal access)
RUN useradd -m -s /bin/bash -G tty martinica

# Project directory (matches the plan: /home/projects/Martinica)
RUN mkdir -p /home/projects/Martinica && \
    chown -R martinica:martinica /home/projects

# Copy project files
COPY --chown=martinica:martinica . /home/projects/Martinica/

# Copy built frontend from Stage 1
COPY --from=frontend-build --chown=martinica:martinica \
    /build/apps/web-server/static/ \
    /home/projects/Martinica/apps/web-server/static/

# Switch to non-root user for remaining setup
USER martinica

# Create single Python venv (both web-server and backend share it,
# because agent_service.py spawns backend scripts via sys.executable)
RUN python3 -m venv /home/projects/Martinica/.venv

# Install both requirements into the same venv
RUN /home/projects/Martinica/.venv/bin/pip install --no-cache-dir \
    -r /home/projects/Martinica/apps/web-server/requirements.txt \
    -r /home/projects/Martinica/apps/backend/requirements.txt

# Git config (required for worktree operations inside the container)
RUN git config --global user.name "Martinica" && \
    git config --global user.email "martinica@container"

# Create data directory for persistent state
RUN mkdir -p /home/martinica/.martinica

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
ENV MARTINICA_HOST=0.0.0.0 \
    MARTINICA_PORT=8000 \
    MARTINICA_BACKEND_PATH=/home/projects/Martinica/apps/backend \
    MARTINICA_PROJECTS_DATA_DIR=/home/martinica/.martinica \
    MARTINICA_DEFAULT_SHELL=/bin/bash \
    PYTHONUNBUFFERED=1 \
    # Ensure venv Python is used everywhere
    PATH="/home/projects/Martinica/.venv/bin:$PATH"

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

WORKDIR /home/projects/Martinica/apps/web-server

CMD ["python", "-m", "server.main"]
