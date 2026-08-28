from __future__ import annotations

from PySide6.QtCore import QSettings

from app.core.settings_manager import SettingsManager, ThemeMode
from app.services.startup_service import StartupService
from app.services.theme_service import ThemeService
from app.ui.pages.settings_page import SettingsPage


def make_settings(tmp_path) -> SettingsManager:
    backend = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    backend.clear()
    return SettingsManager(backend)


def test_settings_defaults_and_persistence(tmp_path):
    settings = make_settings(tmp_path)
    assert settings.theme is ThemeMode.SYSTEM
    assert settings.refresh_interval == 30
    assert not settings.startup_enabled
    assert not settings.advanced_mode

    settings.theme = ThemeMode.DARK
    settings.refresh_interval = 10
    settings.startup_enabled = True
    settings.advanced_mode = True
    settings.sync()

    reloaded = SettingsManager(
        QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    )
    assert reloaded.theme is ThemeMode.DARK
    assert reloaded.refresh_interval == 10
    assert reloaded.startup_enabled
    assert reloaded.advanced_mode


def test_settings_rejects_unsupported_refresh_interval(tmp_path):
    settings = make_settings(tmp_path)
    try:
        settings.refresh_interval = 7
    except ValueError:
        pass
    else:
        raise AssertionError("unsupported refresh interval was accepted")


class RegistryKey:
    def __init__(self, registry, path):
        self.registry = registry
        self.path = path

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None


class FakeRegistry:
    HKEY_CURRENT_USER = object()
    KEY_READ = 1
    KEY_SET_VALUE = 2
    REG_SZ = 1
    REG_BINARY = 3

    def __init__(self):
        self.values = {}

    def OpenKey(self, _root, path, *_args):
        if not self.values.get(path):
            raise FileNotFoundError
        return RegistryKey(self, path)

    def CreateKeyEx(self, _root, path, *_args):
        self.values.setdefault(path, {})
        return RegistryKey(self, path)

    def QueryValueEx(self, key, name):
        if name not in self.values[key.path]:
            raise FileNotFoundError
        return self.values[key.path][name]

    def SetValueEx(self, key, name, _reserved, kind, value):
        self.values[key.path][name] = (value, kind)

    def DeleteValue(self, key, name):
        if name not in self.values[key.path]:
            raise FileNotFoundError
        del self.values[key.path][name]


def test_startup_service_round_trip():
    registry = FakeRegistry()
    service = StartupService(registry=registry, command='"mijia-desktop.exe"')
    assert not service.is_enabled()
    service.set_enabled(True)
    assert service.is_enabled()
    assert registry.values[
        r"Software\Microsoft\Windows\CurrentVersion\Run"
    ]["Mijia Desktop"][0] == '"mijia-desktop.exe"'
    assert registry.values[
        r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"
    ]["Mijia Desktop"][0].startswith(b"\x02")
    service.set_enabled(False)
    assert not service.is_enabled()


def test_settings_page_emits_selected_values(qtbot, tmp_path):
    page = SettingsPage(make_settings(tmp_path))
    qtbot.addWidget(page)
    themes = []
    intervals = []
    page.theme_changed.connect(themes.append)
    page.refresh_interval_changed.connect(intervals.append)

    page.theme_combo.setCurrentIndex(page.theme_combo.findData("dark"))
    page.refresh_combo.setCurrentIndex(page.refresh_combo.findData(5))

    assert themes == ["dark"]
    assert intervals == [5]


def test_theme_service_applies_light_and_dark_styles(qapp):
    service = ThemeService(qapp)
    service.apply(ThemeMode.DARK)
    assert "#17191c" in qapp.styleSheet()
    service.apply(ThemeMode.LIGHT)
    assert "#17191c" not in qapp.styleSheet()
