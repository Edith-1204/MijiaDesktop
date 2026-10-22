"""OS-protected storage for mijiaAPI authentication data."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

from app.core.exceptions import AuthenticationError
from app.utils.paths import encrypted_auth_file, roaming_data_directory


CRYPTPROTECT_LOCAL_MACHINE = 0x4


class _TemporaryCredentialStore:
    @property
    def working_directory(self) -> Path:
        """Return the private temporary directory used during this session."""
        return self.prepare().parent

    def close(self) -> None:
        """Remove plaintext authentication material."""
        if self._temporary_directory is not None:
            self._temporary_directory.cleanup()
        self._temporary_directory = None
        self._plain_path = None

    def __enter__(self) -> _TemporaryCredentialStore:
        self.prepare()
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


class WindowsCredentialStore(_TemporaryCredentialStore):
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


class MacOSCredentialStore(_TemporaryCredentialStore):
    """Local AES-GCM credentials and key, restricted to the current user."""

    MAGIC = b"MJDA1"

    def __init__(self, protected_path: Path | None = None) -> None:
        self.protected_path = protected_path or (
            roaming_data_directory() / "credentials" / "auth.dat"
        )
        self.key_path = self.protected_path.with_suffix(".key")
        self._temporary_directory = None
        self._plain_path = None

    @property
    def exists(self) -> bool:
        return self.protected_path.is_file()

    def prepare(self) -> Path:
        if self._plain_path is not None:
            return self._plain_path
        try:
            from Crypto.Cipher import AES

            self._temporary_directory = tempfile.TemporaryDirectory(prefix="mijia-desktop-auth-")
            self._plain_path = Path(self._temporary_directory.name) / "auth.json"
            if self.exists:
                data = self.protected_path.read_bytes()
                if not data.startswith(self.MAGIC) or len(data) < 33:
                    raise ValueError("Invalid credential container")
                nonce, tag, ciphertext = data[5:17], data[17:33], data[33:]
                cipher = AES.new(self.key_path.read_bytes(), AES.MODE_GCM, nonce=nonce)
                cipher.update(self.MAGIC)
                plain = cipher.decrypt_and_verify(ciphertext, tag)
                self._plain_path.touch(mode=0o600)
                self._plain_path.write_bytes(plain)
            return self._plain_path
        except Exception as error:
            self.close()
            raise AuthenticationError("无法读取本机米家登录状态，请重新登录") from error

    def persist(self) -> None:
        if self._plain_path is None or not self._plain_path.is_file():
            return
        staging = None
        try:
            from Crypto.Cipher import AES

            self.protected_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            self.protected_path.parent.chmod(0o700)
            if not self.key_path.exists():
                if self.exists:
                    raise ValueError("Credential key is missing")
                descriptor = os.open(self.key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(os.urandom(32))
                    stream.flush()
                    os.fsync(stream.fileno())
            self.key_path.chmod(0o600)
            cipher = AES.new(self.key_path.read_bytes(), AES.MODE_GCM, nonce=os.urandom(12))
            cipher.update(self.MAGIC)
            ciphertext, tag = cipher.encrypt_and_digest(self._plain_path.read_bytes())
            with tempfile.NamedTemporaryFile(
                dir=self.protected_path.parent, prefix=".auth-", delete=False
            ) as stream:
                staging = Path(stream.name)
                stream.write(self.MAGIC + cipher.nonce + tag + ciphertext)
                stream.flush()
                os.fsync(stream.fileno())
            staging.replace(self.protected_path)
            self.protected_path.chmod(0o600)
        except Exception as error:
            raise AuthenticationError("无法保存本机米家登录状态") from error
        finally:
            if staging is not None:
                staging.unlink(missing_ok=True)

    def clear(self) -> None:
        try:
            self.protected_path.unlink(missing_ok=True)
            self.key_path.unlink(missing_ok=True)
        except OSError as error:
            raise AuthenticationError("无法删除本机米家登录状态") from error
        finally:
            self.close()


def create_credential_store() -> WindowsCredentialStore | MacOSCredentialStore:
    if sys.platform == "darwin":
        return MacOSCredentialStore()
    return WindowsCredentialStore()
