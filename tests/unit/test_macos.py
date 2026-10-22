import plistlib

import pytest

from app.core.exceptions import AuthenticationError, StorageError
from app.mijia.auth import MacOSCredentialStore
from app.services.macos_startup_service import MacOSStartupService
from app.utils import paths


def test_local_credentials_round_trip_permissions_and_cleanup(tmp_path):
    protected = tmp_path / "private" / "auth.dat"
    store = MacOSCredentialStore(protected)
    assert not store.exists
    path = store.prepare()
    secret = b'{"serviceToken":"test-only"}'
    path.write_bytes(secret)
    store.persist()
    store.close()
    assert not path.parent.exists()
    assert secret not in protected.read_bytes()
    assert protected.stat().st_mode & 0o777 == 0o600
    assert protected.parent.stat().st_mode & 0o777 == 0o700
    assert store.key_path.stat().st_mode & 0o777 == 0o600
    restored = MacOSCredentialStore(protected)
    assert restored.exists
    assert restored.prepare().read_bytes() == secret
    restored.clear()
    assert not protected.exists()
    assert not restored.key_path.exists()
    assert not restored.exists
    restored.close()


@pytest.mark.parametrize("damage", ["ciphertext", "missing-key", "wrong-key"])
def test_local_credentials_reject_damage(tmp_path, damage):
    protected = tmp_path / "private" / "auth.dat"
    store = MacOSCredentialStore(protected)
    store.prepare().write_text("test-only")
    store.persist()
    store.close()
    if damage == "ciphertext":
        data = bytearray(protected.read_bytes())
        data[-1] ^= 1
        protected.write_bytes(data)
    elif damage == "missing-key":
        store.key_path.unlink()
    else:
        store.key_path.write_bytes(b"x" * 32)
    restored = MacOSCredentialStore(protected)
    with pytest.raises(AuthenticationError):
        restored.prepare()
    assert restored._temporary_directory is None
    assert restored._plain_path is None


def test_launch_agent_round_trip_and_migration(tmp_path):
    path = tmp_path / "LaunchAgents" / "mijia.plist"
    old = MacOSStartupService(agent_path=path, arguments=["/Old Path/app", "--hidden"])
    assert not old.is_enabled()
    old.set_enabled(True)
    new = MacOSStartupService(agent_path=path, arguments=["/New Path/app", "--hidden"])
    assert new.ensure_current_registration()
    with path.open("rb") as stream:
        data = plistlib.load(stream)
    assert data["ProgramArguments"] == ["/New Path/app", "--hidden"]
    assert data["RunAtLoad"] is True
    assert data["LimitLoadToSessionType"] == "Aqua"
    new.set_enabled(False)
    assert not new.is_enabled()
    assert not path.exists()


def test_malformed_launch_agent_reports_storage_error(tmp_path):
    path = tmp_path / "bad.plist"
    path.write_text("broken")
    with pytest.raises(StorageError):
        MacOSStartupService(agent_path=path).is_enabled()


def test_macos_data_paths(monkeypatch, tmp_path):
    monkeypatch.setattr(paths.sys, "platform", "darwin")
    monkeypatch.setattr(paths.Path, "home", lambda: tmp_path)
    assert paths.local_data_directory() == tmp_path / "Library/Application Support/MijiaDesktop"
    assert paths.roaming_data_directory() == paths.local_data_directory()
    assert paths.log_directory() == tmp_path / "Library/Logs/MijiaDesktop"


def test_window_can_restore_after_close_to_menu_bar(qtbot, monkeypatch):
    from app.ui.main_window import MainWindow

    window = MainWindow(auto_refresh=False, enable_tray=True)
    qtbot.addWidget(window)
    window.tray_service.available = True
    monkeypatch.setattr(window.tray_service, "show_hidden_message", lambda: None)
    window.show()
    assert not window.closed_to_tray
    window.close()
    assert window.closed_to_tray
    assert not window.isVisible()
    window.restore_from_tray()
    assert window.isVisible()
    assert not window.closed_to_tray
    window._allow_exit = True
