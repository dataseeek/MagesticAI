"""
Audit logging service for security-relevant actions.

Provides functions to create immutable audit log entries in the database.
All logging functions are designed to be non-blocking and failure-safe --
a failed audit log write will never crash the calling operation.

Usage::

    from ..services.audit_service import log_audit_event, ACTION_USER_LOGIN

    # Within a route handler that already has a db session:
    await log_audit_event(
        db=db,
        user_id=user.id,
        org_id=org.id,
        action=ACTION_USER_LOGIN,
        resource_type="user",
        resource_id=user.id,
        ip=request.client.host,
    )

    # From background code without a request-scoped session:
    await log_audit_event_bg(
        user_id=user.id,
        org_id=org.id,
        action=ACTION_USER_LOGIN,
        resource_type="user",
        resource_id=user.id,
    )
"""

import json
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from ..database import AuditLog
from ..database.engine import async_session_factory

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Action constants
# ---------------------------------------------------------------------------

ACTION_USER_REGISTER = "user.register"
ACTION_USER_LOGIN = "user.login"

ACTION_ORG_CREATE = "org.create"
ACTION_ORG_UPDATE = "org.update"
ACTION_ORG_DELETE = "org.delete"

ACTION_MEMBER_INVITE = "member.invite"
ACTION_MEMBER_REMOVE = "member.remove"
ACTION_MEMBER_ROLE_CHANGE = "member.role_change"

ACTION_PROJECT_CREATE = "project.create"
ACTION_PROJECT_DELETE = "project.delete"

ACTION_TASK_CREATE = "task.create"
ACTION_TASK_START = "task.start"
ACTION_TASK_MERGE = "task.merge"

ACTION_API_KEY_CREATE = "api_key.create"
ACTION_API_KEY_REVOKE = "api_key.revoke"


# ---------------------------------------------------------------------------
# Core audit logging function
# ---------------------------------------------------------------------------


async def log_audit_event(
    db: AsyncSession,
    *,
    user_id: str | None = None,
    org_id: str | None = None,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    details: dict | None = None,
    ip: str | None = None,
) -> None:
    """Create an audit log entry using the provided database session.

    This function is wrapped in a try/except so that audit logging
    failures never propagate to the calling code.  A warning is logged
    instead.

    Parameters
    ----------
    db:
        An active ``AsyncSession`` (typically the request-scoped session).
    user_id:
        The ID of the user who performed the action, or ``None`` for
        system-initiated events.
    org_id:
        The ID of the organization the action belongs to, or ``None``
        for org-independent events (e.g., user registration).
    action:
        A dot-separated action identifier (e.g., ``"user.login"``).
        Use the ``ACTION_*`` constants defined in this module.
    resource_type:
        The type of resource affected (e.g., ``"user"``, ``"org"``,
        ``"project"``).
    resource_id:
        The ID of the specific resource affected, if applicable.
    details:
        Optional dictionary of extra context to store as JSON.
    ip:
        The IP address of the client, if available.
    """
    try:
        entry = AuditLog(
            user_id=user_id,
            org_id=org_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details_json=json.dumps(details) if details is not None else None,
            ip=ip,
        )
        db.add(entry)
        await db.flush()
    except Exception:
        logger.warning(
            "Failed to write audit log entry: action=%s resource_type=%s resource_id=%s",
            action,
            resource_type,
            resource_id,
            exc_info=True,
        )


# ---------------------------------------------------------------------------
# Background audit logging (creates its own session)
# ---------------------------------------------------------------------------


async def log_audit_event_bg(
    *,
    user_id: str | None = None,
    org_id: str | None = None,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    details: dict | None = None,
    ip: str | None = None,
) -> None:
    """Create an audit log entry using a self-managed database session.

    This is useful when you need to log an audit event outside of a
    request-scoped session (e.g., from a background task, a WebSocket
    handler, or any code that does not have access to the FastAPI
    ``Depends(get_db)`` dependency).

    The session is created, committed, and closed within this function.
    Like :func:`log_audit_event`, failures are caught and logged as
    warnings so they never crash the caller.

    Parameters are identical to :func:`log_audit_event` except there is
    no ``db`` parameter.
    """
    try:
        async with async_session_factory() as session:
            entry = AuditLog(
                user_id=user_id,
                org_id=org_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details_json=json.dumps(details) if details is not None else None,
                ip=ip,
            )
            session.add(entry)
            await session.commit()
    except Exception:
        logger.warning(
            "Failed to write background audit log entry: action=%s resource_type=%s resource_id=%s",
            action,
            resource_type,
            resource_id,
            exc_info=True,
        )
