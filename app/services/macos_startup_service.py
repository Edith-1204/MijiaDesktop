"""Register a per-user LaunchAgent for the next macOS login."""

from __future__ import annotations

import os
import plistlib
import sys
from pathlib import Path

from app.core.exceptions import StorageError


class MacOSStartupService:
    LABEL = "io.github.Edith-1204.MijiaDesktop"

    def __init__(
        self, *, agent_path: Path | None = None, arguments: list[str] | None = None
    ) -> None:
        self.agent_path = agent_path or (
            Path.home() / "Library" / "LaunchAgents" / f"{self.LABEL}.plist"
        )
        self.arguments = arguments or (
            [sys.executable, "--hidden"]
            if getattr(sys, "frozen", False)
            else [sys.executable, "-m", "app.main", "--hidden"]
        )
        self.working_directory = str(Path(__file__).resolve().parents[2])

    def _read(self) -> dict:
        try:
            with self.agent_path.open("rb") as stream:
                data = plistlib.load(stream)
            if not isinstance(data, dict):
                raise ValueError("LaunchAgent must be a property list dictionary")
            return data
        except FileNotFoundError:
            return {}
        except (OSError, ValueError, plistlib.InvalidFileException) as error:
            raise StorageError("无法读取 macOS 登录启动设置") from error

    def is_enabled(self) -> bool:
        data = self._read()
        return data.get("Label") == self.LABEL and data.get("RunAtLoad") is True

    def ensure_current_registration(self) -> bool:
        if not self.is_enabled():
            return False
        data = self._read()
        if (
            data.get("ProgramArguments") != self.arguments
            or data.get("WorkingDirectory") != self.working_directory
        ):
            self.set_enabled(True)
        return True

    def set_enabled(self, enabled: bool) -> None:
        staging = self.agent_path.with_suffix(".tmp")
        try:
            if not enabled:
                self.agent_path.unlink(missing_ok=True)
                return
            self.agent_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "Label": self.LABEL,
                "ProgramArguments": self.arguments,
                "WorkingDirectory": self.working_directory,
                "RunAtLoad": True,
                "ProcessType": "Interactive",
                "LimitLoadToSessionType": "Aqua",
            }
            with staging.open("wb") as stream:
                plistlib.dump(data, stream)
            os.chmod(staging, 0o600)
            staging.replace(self.agent_path)
        except OSError as error:
            raise StorageError("无法修改 macOS 登录启动设置") from error
        finally:
            staging.unlink(missing_ok=True)
