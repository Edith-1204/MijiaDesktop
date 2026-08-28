"""Persistent user settings backed by QSettings."""

from __future__ import annotations

from enum import StrEnum

from PySide6.QtCore import QSettings


class ThemeMode(StrEnum):
    SYSTEM = "system"
    LIGHT = "light"
    DARK = "dark"


REFRESH_INTERVALS = (5, 10, 30, 60, 120, 0)


class SettingsManager:
    def __init__(self, settings: QSettings | None = None) -> None:
        self._settings = settings or QSettings()

    @property
    def theme(self) -> ThemeMode:
        value = str(self._settings.value("appearance/theme", ThemeMode.SYSTEM.value))
        try:
            return ThemeMode(value)
        except ValueError:
            return ThemeMode.SYSTEM

    @theme.setter
    def theme(self, value: ThemeMode | str) -> None:
        self._settings.setValue("appearance/theme", ThemeMode(value).value)

    @property
    def refresh_interval(self) -> int:
        value = int(self._settings.value("state/refresh_interval", 30))
        return value if value in REFRESH_INTERVALS else 30

    @refresh_interval.setter
    def refresh_interval(self, value: int) -> None:
        if value not in REFRESH_INTERVALS:
            raise ValueError("unsupported refresh interval")
        self._settings.setValue("state/refresh_interval", value)

    @property
    def advanced_mode(self) -> bool:
        return self._settings.value("developer/advanced_mode", False, type=bool)

    @advanced_mode.setter
    def advanced_mode(self, value: bool) -> None:
        self._settings.setValue("developer/advanced_mode", bool(value))

    @property
    def startup_enabled(self) -> bool:
        return self._settings.value("system/startup_enabled", False, type=bool)

    @startup_enabled.setter
    def startup_enabled(self, value: bool) -> None:
        self._settings.setValue("system/startup_enabled", bool(value))

    def sync(self) -> None:
        self._settings.sync()
