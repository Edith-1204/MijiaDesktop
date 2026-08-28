"""Mijia Desktop executable entry point."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from app.application import create_application
from app.ui.main_window import MainWindow


def main() -> int:
    """Start the Qt application and return its exit code."""
    application = create_application(sys.argv)
    window = MainWindow()
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())

