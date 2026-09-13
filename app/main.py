"""Mijia Desktop executable entry point."""

from __future__ import annotations

import sys

from app.core.runtime import ensure_standard_streams

ensure_standard_streams()

from PySide6.QtWidgets import QApplication

from app.application import create_application
from app.core.account_manager import AccountManager
from app.core.device_manager import DeviceManager
from app.core.exceptions import MijiaDesktopError
from app.core.settings_manager import SettingsManager
from app.mijia.adapter import MijiaAdapter
from app.services.startup_service import StartupService
from app.services.theme_service import ThemeService
from app.storage.repository import FavoritesRepository
from app.storage.spec_cache import DeviceSpecCache
from app.ui.main_window import MainWindow


HIDDEN_STARTUP_ARGUMENT = "--hidden"


def _hidden_start_requested(arguments: list[str]) -> bool:
    return HIDDEN_STARTUP_ARGUMENT in arguments[1:]


def _qt_arguments(arguments: list[str]) -> list[str]:
    return [argument for argument in arguments if argument != HIDDEN_STARTUP_ARGUMENT]


def _can_remain_hidden(window: MainWindow) -> bool:
    return window.tray_service is not None and window.tray_service.available


def main() -> int:
    """Start the Qt application and return its exit code."""
    arguments = list(sys.argv)
    start_hidden = _hidden_start_requested(arguments)
    application = create_application(_qt_arguments(arguments))
    settings = SettingsManager()
    theme_service = ThemeService(application)
    theme_service.apply(settings.theme)
    try:
        adapter = MijiaAdapter()
        repository = FavoritesRepository()
        startup_service = StartupService()
        settings.startup_enabled = startup_service.ensure_current_registration()
        window = MainWindow(
            DeviceManager(
                adapter,
                favorites_repository=repository,
                spec_cache=DeviceSpecCache(),
            ),
            settings_manager=settings,
            theme_service=theme_service,
            startup_service=startup_service,
            account_manager=AccountManager(adapter),
            enable_tray=True,
        )
        application.aboutToQuit.connect(adapter.close)
        application.aboutToQuit.connect(repository.close)
        application.aboutToQuit.connect(settings.sync)
    except MijiaDesktopError as error:
        window = MainWindow(
            auto_refresh=False,
            settings_manager=settings,
            theme_service=theme_service,
        )
        window.devices_page.show_error(str(error))
    if not start_hidden or not _can_remain_hidden(window):
        window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
