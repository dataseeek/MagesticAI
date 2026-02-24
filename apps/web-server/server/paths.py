"""Centralized path helpers for Martinica data directory."""
from pathlib import Path

MARTINICA_DIR = Path.home() / ".martinica"


def get_data_dir() -> Path:
    """Return the Martinica data directory, creating it if needed."""
    MARTINICA_DIR.mkdir(parents=True, exist_ok=True)
    return MARTINICA_DIR


def get_data_file(filename: str) -> Path:
    """Get a file path in the Martinica data directory."""
    return MARTINICA_DIR / filename
