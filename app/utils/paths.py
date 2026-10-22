"""Centralized application data paths."""

from __future__ import annotations

import os
import sys
from pathlib import Path


APP_DIRECTORY_NAME = "MijiaDesktop"


def local_data_directory() -> Path:
    """Return the per-user directory used for logs and cache data."""
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_DIRECTORY_NAME
    root = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local" / "share"))
    return root / APP_DIRECTORY_NAME


def roaming_data_directory() -> Path:
    """Return the per-user directory used for settings and credentials."""
    if sys.platform == "darwin":
        return local_data_directory()
    root = Path(os.environ.get("APPDATA", Path.home() / ".config"))
    return root / APP_DIRECTORY_NAME


def encrypted_auth_file() -> Path:
    """Return the DPAPI-protected authentication data path."""
    return roaming_data_directory() / "auth.dat"


def log_directory() -> Path:
    """Return the application log directory."""
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Logs" / APP_DIRECTORY_NAME
    return local_data_directory() / "logs"
