"""
Magestic AI Web Server - FastAPI Application.

Main entry point for the web server that provides:
- REST API for project/task management
- WebSocket endpoints for real-time streaming
- Static file serving for the React SPA
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles

from .auth import TokenAuthMiddleware
from .config import get_settings
from .database.engine import init_db
from .logging_config import setup_logging
from .routes import (
    api_keys,
    audit,
    auth_routes,
    context,
    email,
    execution,
    files,
    git,
    github,
    notifications,
    organizations,
    projects,
    tasks,
    terminal,
)
from .routes import logs as logs_routes
from .routes import cli_accounts as cli_accounts_routes
from .routes import settings as settings_routes
from .websockets import events as events_ws
from .websockets import logs as logs_ws
from .websockets import progress as progress_ws
from .websockets import terminal as terminal_ws

# Configure logging with file output
settings = get_settings()
setup_logging(log_level="DEBUG" if settings.DEBUG else "INFO")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    settings = get_settings()

    # Startup
    logger.info("Starting Magestic AI Web Server...")
    logger.info(f"Backend path: {settings.BACKEND_PATH}")
    logger.info(f"Projects data dir: {settings.PROJECTS_DATA_DIR}")

    # Ensure data directory exists
    Path(settings.PROJECTS_DATA_DIR).mkdir(parents=True, exist_ok=True)

    # Initialize database (creates tables if needed)
    await init_db()

    yield

    # Shutdown
    logger.info("Shutting down Magestic AI Web Server...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Magestic AI Web API",
        description="Web API for Magestic AI autonomous coding framework",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add token auth middleware
    app.add_middleware(TokenAuthMiddleware)

    # Auth routes (prefix defined in router: /api/auth)
    app.include_router(auth_routes.router)

    # Organization routes (prefix defined in router: /api/orgs)
    app.include_router(organizations.router)

    # API key management (prefix defined in router: /api/keys)
    app.include_router(api_keys.router)

    # Audit log routes (prefix defined in router: /api/orgs)
    app.include_router(audit.router)

    # Notification routes (prefix defined in router: /api/notifications)
    app.include_router(notifications.router)

    # Include API routers
    app.include_router(projects.router, prefix="/api/projects", tags=["Projects"])
    app.include_router(tasks.router, prefix="/api/tasks", tags=["Tasks"])
    # Execution routes also under /api/tasks for frontend compatibility
    app.include_router(execution.router, prefix="/api/tasks", tags=["Task Execution"])
    app.include_router(settings_routes.router, prefix="/api/settings", tags=["Settings"])
    app.include_router(cli_accounts_routes.router, prefix="/api/settings", tags=["CLI Accounts"])
    app.include_router(files.router, prefix="/api/files", tags=["Files"])
    app.include_router(terminal.router, prefix="/api/terminals", tags=["Terminals"])

    # Email OAuth + account management routes (prefix defined in router: /api/email)
    app.include_router(email.router)

    # GitHub routes
    app.include_router(github.router, prefix="/api/github", tags=["GitHub"])

    # Git and utility routes
    app.include_router(git.router, prefix="/api/git", tags=["Git"])
    app.include_router(git.ollama_router, prefix="/api/ollama", tags=["Ollama"])
    app.include_router(git.claude_code_router, prefix="/api/claude-code", tags=["Claude Code"])
    app.include_router(git.mcp_router, prefix="/api/mcp", tags=["MCP"])
    app.include_router(git.updates_router, prefix="/api/updates", tags=["Updates"])

    # Memory infrastructure routes
    app.include_router(context.router, prefix="/api/memory", tags=["Memory"])

    # Logs viewing routes
    app.include_router(logs_routes.router, prefix="/api/logs", tags=["Logs"])

    # Include WebSocket routers
    app.include_router(logs_ws.router, tags=["WebSocket"])
    app.include_router(progress_ws.router, tags=["WebSocket"])
    app.include_router(terminal_ws.router, tags=["WebSocket"])
    app.include_router(events_ws.router, tags=["WebSocket"])

    # Health check endpoint (no auth required)
    @app.get("/api/health")
    async def health_check():
        return {"status": "healthy", "version": "1.0.0"}

    # Mount static files for SPA (if build directory exists)
    static_dir = Path(__file__).parent.parent / "static"
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
    else:
        # Placeholder for development
        @app.get("/")
        async def root():
            return {
                "message": "Magestic AI Web Server",
                "docs": "/docs",
                "note": "Frontend not built yet. Run 'npm run build' in apps/frontend-web/",
            }

    return app


# Create the app instance
app = create_app()


# Add Bearer token auth to OpenAPI schema so Swagger UI shows the Authorize button
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    openapi_schema.setdefault("components", {})["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT access token or legacy API token",
        }
    }
    openapi_schema["security"] = [{"BearerAuth": []}]
    app.openapi_schema = openapi_schema
    return openapi_schema


app.openapi = custom_openapi


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()

    # Build uvicorn config
    uvicorn_config = {
        "app": "server.main:app",
        "host": settings.HOST,
        "port": settings.PORT,
        "reload": settings.DEBUG,
    }

    # Add SSL if enabled
    if settings.SSL_ENABLED:
        uvicorn_config["ssl_certfile"] = settings.SSL_CERTFILE
        uvicorn_config["ssl_keyfile"] = settings.SSL_KEYFILE
        logger.info(f"HTTPS enabled with certificate: {settings.SSL_CERTFILE}")

    uvicorn.run(**uvicorn_config)
