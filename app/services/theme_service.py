"""Application theme selection and system color-scheme tracking."""

from __future__ import annotations

from PySide6.QtCore import QObject, Qt
from PySide6.QtWidgets import QApplication

from app.core.settings_manager import ThemeMode
from app.ui.style import load_stylesheet


class ThemeService(QObject):
    def __init__(self, application: QApplication, parent=None) -> None:
        super().__init__(parent)
        self.application = application
        self.mode = ThemeMode.SYSTEM
        application.styleHints().colorSchemeChanged.connect(self._system_changed)

    def apply(self, mode: ThemeMode | str) -> None:
        self.mode = ThemeMode(mode)
        resolved = self.mode
        if resolved is ThemeMode.SYSTEM:
            resolved = (
                ThemeMode.DARK
                if self.application.styleHints().colorScheme() is Qt.ColorScheme.Dark
                else ThemeMode.LIGHT
            )
        self.application.setStyleSheet(load_stylesheet(resolved.value))

    def _system_changed(self, _scheme) -> None:
        if self.mode is ThemeMode.SYSTEM:
            self.apply(self.mode)
