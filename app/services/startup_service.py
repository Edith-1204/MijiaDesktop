"""Per-user Windows startup registration."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

from app.core.exceptions import StorageError


RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APPROVED_RUN_KEY = (
    r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"
)
VALUE_NAME = "Mijia Desktop"
LEGACY_VALUE_NAME = "MijiaDesktop"
ENABLED_APPROVAL = b"\x02" + (b"\x00" * 11)


class StartupService:
    def __init__(
        self,
        registry=None,
        command: str | None = None,
        legacy_command: str | None = None,
    ) -> None:
        if registry is None:
            if os.name != "nt":
                raise RuntimeError("Startup registration requires Windows")
            import winreg

            registry = winreg
        self._registry = registry
        self._accept_versioned_executable = command is None and bool(
            getattr(sys, "frozen", False)
        )
        if command is None:
            self.command = self._default_command(hidden=True)
            self.legacy_command = self._default_command(hidden=False)
        else:
            self.command = command
            self.legacy_command = legacy_command or command

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
                        if self._matches_registered_command(value):
                            return True
                    except FileNotFoundError:
                        continue
                return False
        except FileNotFoundError:
            return False
        except OSError as error:
            raise StorageError("无法读取开机启动设置") from error

    def ensure_current_registration(self) -> bool:
        """Migrate an enabled legacy entry to the silent startup command."""
        if not self.is_enabled():
            return False
        if not self._uses_current_command():
            self.set_enabled(True)
        return True

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

    def _uses_current_command(self) -> bool:
        try:
            with self._registry.OpenKey(
                self._registry.HKEY_CURRENT_USER,
                RUN_KEY,
                0,
                self._registry.KEY_READ,
            ) as key:
                value, _kind = self._registry.QueryValueEx(key, VALUE_NAME)
                return value == self.command
        except FileNotFoundError:
            return False
        except OSError as error:
            raise StorageError("无法读取开机启动设置") from error

    def _matches_registered_command(self, value: object) -> bool:
        if value in {self.command, self.legacy_command}:
            return True
        if not self._accept_versioned_executable or not isinstance(value, str):
            return False
        candidate = value.strip()
        if candidate.casefold().endswith(" --hidden"):
            candidate = candidate[: -len(" --hidden")].rstrip()
        candidate = candidate.strip('"')
        return bool(
            re.fullmatch(
                r"MijiaDesktop(?:-[0-9][0-9A-Za-z.-]*)?\.exe",
                Path(candidate).name,
                flags=re.IGNORECASE,
            )
        )

    @staticmethod
    def _default_command(*, hidden: bool) -> str:
        executable = sys.executable
        if getattr(sys, "frozen", False):
            arguments = [executable]
            if hidden:
                arguments.append("--hidden")
            return subprocess.list2cmdline(arguments)
        pythonw = os.path.join(os.path.dirname(executable), "pythonw.exe")
        if os.path.isfile(pythonw):
            executable = pythonw
        arguments = [executable, "-m", "app.main"]
        if hidden:
            arguments.append("--hidden")
        return subprocess.list2cmdline(arguments)
