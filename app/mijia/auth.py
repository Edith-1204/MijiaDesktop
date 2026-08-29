"""Windows DPAPI-backed storage for mijiaAPI authentication data."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from app.core.exceptions import AuthenticationError
from app.utils.paths import encrypted_auth_file


CRYPTPROTECT_LOCAL_MACHINE = 0x4


class WindowsCredentialStore:
    """Expose auth JSON only in a private temporary directory while in use."""

    def __init__(self, protected_path: Path | None = None) -> None:
        if os.name != "nt":
            raise RuntimeError("Mijia Desktop credential storage currently requires Windows")
        self.protected_path = protected_path or encrypted_auth_file()
        self._temporary_directory: tempfile.TemporaryDirectory[str] | None = None
        self._plain_path: Path | None = None

    @property
    def exists(self) -> bool:
        return self.protected_path.is_file()

    @property
    def working_directory(self) -> Path:
        """Return the private temporary directory used during this session."""
        return self.prepare().parent

    def prepare(self) -> Path:
        """Create a temporary auth path and decrypt existing credentials into it."""
        if self._plain_path is not None:
            return self._plain_path

        self._temporary_directory = tempfile.TemporaryDirectory(prefix="mijia-desktop-auth-")
        self._plain_path = Path(self._temporary_directory.name) / "auth.json"
        if self.exists:
            try:
                import win32crypt

                unprotected_result = win32crypt.CryptUnprotectData(
                    self.protected_path.read_bytes(),
                    None,
                    None,
                    None,
                    0,
                )
                plain_data = (
                    unprotected_result[1]
                    if isinstance(unprotected_result, tuple)
                    else unprotected_result
                )
                self._plain_path.write_bytes(plain_data)
            except Exception as error:
                self.close()
                raise AuthenticationError("无法解密已保存的米家登录状态") from error
        return self._plain_path

    def persist(self) -> None:
        """Encrypt the current temporary auth JSON for the Windows user."""
        if self._plain_path is None or not self._plain_path.is_file():
            return
        try:
            import win32crypt

            plain_data = self._plain_path.read_bytes()
            try:
                protected_result = win32crypt.CryptProtectData(
                    plain_data,
                    "Mijia Desktop authentication",
                    None,
                    None,
                    None,
                    0,
                )
            except Exception as error:
                # Windows service/sandbox profiles may not have a user DPAPI master key.
                # Machine-scope DPAPI still encrypts at rest; the file remains protected
                # by the current user's AppData ACL.
                if not error.args or error.args[0] != 2:
                    raise
                protected_result = win32crypt.CryptProtectData(
                    plain_data,
                    "Mijia Desktop authentication",
                    None,
                    None,
                    None,
                    CRYPTPROTECT_LOCAL_MACHINE,
                )
            protected_data = (
                protected_result[1]
                if isinstance(protected_result, tuple)
                else protected_result
            )
            self.protected_path.parent.mkdir(parents=True, exist_ok=True)
            staging_path = self.protected_path.with_suffix(".tmp")
            staging_path.write_bytes(protected_data)
            staging_path.replace(self.protected_path)
        except OSError as error:
            raise AuthenticationError("无法安全保存米家登录状态") from error

    def clear(self) -> None:
        """Delete both protected and temporary authentication material."""
        self.protected_path.unlink(missing_ok=True)
        if self._plain_path is not None:
            self._plain_path.unlink(missing_ok=True)
        if self._temporary_directory is not None:
            self._temporary_directory.cleanup()
        self._temporary_directory = None
        self._plain_path = None

    def close(self) -> None:
        """Remove plaintext authentication material."""
        if self._temporary_directory is not None:
            self._temporary_directory.cleanup()
        self._temporary_directory = None
        self._plain_path = None

    def __enter__(self) -> WindowsCredentialStore:
        self.prepare()
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()
