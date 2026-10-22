"""Application bootstrap helpers."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from app import __version__
from app.utils.logger import configure_logging


def load_application_icon() -> QIcon:
    """Use the macOS rounded tile for the app and Dock; preserve the Windows icon."""
    name = "mijia-macos.png" if sys.platform == "darwin" else "mijia.ico"
    icon_path = Path(__file__).resolve().parents[1] / "resources" / "icons" / name
    return QIcon(str(icon_path))


def create_application(arguments: Sequence[str] | None = None) -> QApplication:
    """Create or reuse the process-wide Qt application instance."""
    configure_logging()
    existing = QApplication.instance()
    application = existing or QApplication(list(arguments or []))
    application.setApplicationName("Mijia Desktop")
    application.setApplicationDisplayName("米家桌面控制中心")
    application.setApplicationVersion(__version__)
    application.setOrganizationName("Mijia Desktop")
    application.setWindowIcon(load_application_icon())
    return application
