"""Centralized path helpers for MagesticAI data directory."""
from pathlib import Path

MAGESTIC_AI_DIR = Path.home() / ".magestic-ai"


def get_data_dir() -> Path:
    """Return the MagesticAI data directory, creating it if needed."""
    MAGESTIC_AI_DIR.mkdir(parents=True, exist_ok=True)
    return MAGESTIC_AI_DIR


def get_data_file(filename: str) -> Path:
    """Get a file path in the MagesticAI data directory."""
    return MAGESTIC_AI_DIR / filename
