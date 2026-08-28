"""Per-user Windows startup registration."""

from __future__ import annotations

import os
import subprocess
import sys

from app.core.exceptions import StorageError


RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APPROVED_RUN_KEY = (
    r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"
)
VALUE_NAME = "Mijia Desktop"
LEGACY_VALUE_NAME = "MijiaDesktop"
ENABLED_APPROVAL = b"\x02" + (b"\x00" * 11)


class StartupService:
    def __init__(self, registry=None, command: str | None = None) -> None:
        if registry is None:
            if os.name != "nt":
                raise RuntimeError("Startup registration requires Windows")
            import winreg

            registry = winreg
        self._registry = registry
        self.command = command or self._default_command()

    def is_enabled(self) -> bool:
        try:
            with self._registry.OpenKey(
                self._registry.HKEY_CURRENT_USER,
                RUN_KEY,
                0,
                self._registry.KEY_READ,
            ) as key:
                for name in (VALUE_NAME, LEGACY_VALUE_NAME):
                    try:
                        value, _kind = self._registry.QueryValueEx(key, name)
                        if value == self.command:
                            return True
                    except FileNotFoundError:
                        continue
                return False
        except FileNotFoundError:
            return False
        except OSError as error:
            raise StorageError("无法读取开机启动设置") from error

    def set_enabled(self, enabled: bool) -> None:
        try:
            with self._registry.CreateKeyEx(
                self._registry.HKEY_CURRENT_USER,
                RUN_KEY,
                0,
                self._registry.KEY_SET_VALUE,
            ) as key:
                if enabled:
                    self._registry.SetValueEx(
                        key,
                        VALUE_NAME,
                        0,
                        self._registry.REG_SZ,
                        self.command,
                    )
                for name in (
                    (LEGACY_VALUE_NAME,) if enabled else (VALUE_NAME, LEGACY_VALUE_NAME)
                ):
                    try:
                        self._registry.DeleteValue(key, name)
                    except FileNotFoundError:
                        pass
            with self._registry.CreateKeyEx(
                self._registry.HKEY_CURRENT_USER,
                APPROVED_RUN_KEY,
                0,
                self._registry.KEY_SET_VALUE,
            ) as key:
                if enabled:
                    self._registry.SetValueEx(
                        key,
                        VALUE_NAME,
                        0,
                        self._registry.REG_BINARY,
                        ENABLED_APPROVAL,
                    )
                for name in (
                    (LEGACY_VALUE_NAME,) if enabled else (VALUE_NAME, LEGACY_VALUE_NAME)
                ):
                    try:
                        self._registry.DeleteValue(key, name)
                    except FileNotFoundError:
                        pass
        except OSError as error:
            raise StorageError("无法修改开机启动设置") from error

    @staticmethod
    def _default_command() -> str:
        executable = sys.executable
        if getattr(sys, "frozen", False):
            return subprocess.list2cmdline([executable])
        pythonw = os.path.join(os.path.dirname(executable), "pythonw.exe")
        if os.path.isfile(pythonw):
            executable = pythonw
        return subprocess.list2cmdline([executable, "-m", "app.main"])
