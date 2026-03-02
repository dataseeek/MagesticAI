"""Backward compatibility shim — re-exports from providers.types."""
from providers.types import (  # noqa: F401
    TextBlock,
    ToolUseBlock,
    ToolResultBlock,
    AssistantMessage,
    UserMessage,
)

__all__ = [
    "TextBlock",
    "ToolUseBlock",
    "ToolResultBlock",
    "AssistantMessage",
    "UserMessage",
]
