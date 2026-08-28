"""Mijia Desktop executable entry point."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from app.application import create_application
from app.core.device_manager import DeviceManager
from app.core.exceptions import MijiaDesktopError
from app.mijia.adapter import MijiaAdapter
from app.storage.repository import FavoritesRepository
from app.storage.spec_cache import DeviceSpecCache
from app.ui.main_window import MainWindow


def main() -> int:
    """Start the Qt application and return its exit code."""
    application = create_application(sys.argv)
    try:
        adapter = MijiaAdapter()
        repository = FavoritesRepository()
        window = MainWindow(
            DeviceManager(
                adapter,
                favorites_repository=repository,
                spec_cache=DeviceSpecCache(),
            ),
            enable_tray=True,
        )
        application.aboutToQuit.connect(adapter.close)
        application.aboutToQuit.connect(repository.close)
    except MijiaDesktopError as error:
        window = MainWindow(auto_refresh=False)
        window.devices_page.show_error(str(error))
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
