"""
Database package for Claude Code Manager Web multi-user system.

Provides SQLAlchemy 2.x async models and engine configuration
backed by SQLite (aiosqlite) with WAL mode for concurrent access.
"""

from .engine import get_db, init_db
from .models import (
    ApiKey,
    AuditLog,
    Base,
    Organization,
    OrgMember,
    Project,
    Task,
    User,
)

__all__ = [
    # Engine
    "init_db",
    "get_db",
    # Models
    "Base",
    "User",
    "Organization",
    "OrgMember",
    "Project",
    "Task",
    "ApiKey",
    "AuditLog",
]
