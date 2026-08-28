"""The sole boundary between Mijia Desktop and mijiaAPI."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

from app.core.exceptions import (
    ActionError,
    AuthenticationError,
    DeviceOfflineError,
    MijiaDesktopError,
    NetworkError,
    PropertyReadError,
    PropertyWriteError,
    UnsupportedDeviceError,
)
from app.mijia.auth import WindowsCredentialStore
from app.utils.logger import get_logger


logger = get_logger(__name__)
OFFLINE_CODES = {-10007, -704042011, -704053036, -704083036}


class MijiaAPIClient(Protocol):
    """Subset of mijiaAPI used by the adapter."""

    auth_data_path: Path

    @property
    def available(self) -> bool: ...

    def login(self) -> dict[str, Any]: ...

    def _get_qr_login_data(self) -> dict[str, Any]: ...

    def _complete_qr_login(self, login_data: dict[str, Any]) -> dict[str, Any]: ...

    def get_devices_list(self) -> list[dict[str, Any]]: ...

    def get_devices_prop(self, data: dict[str, Any] | list[dict[str, Any]]) -> Any: ...

    def set_devices_prop(self, data: dict[str, Any] | list[dict[str, Any]]) -> Any: ...

    def run_action(self, data: dict[str, Any] | list[dict[str, Any]]) -> Any: ...


def _default_api_factory(auth_path: Path) -> MijiaAPIClient:
    from mijiaAPI import mijiaAPI

    return mijiaAPI(str(auth_path))


def _default_spec_loader(model: str, cache_path: Path) -> dict[str, Any]:
    from mijiaAPI import get_device_info

    return get_device_info(model, cache_path=cache_path)


def _default_qr_fetcher(url: str) -> bytes:
    import requests

    response = requests.get(url, timeout=15)
    response.raise_for_status()
    content_type = response.headers.get("content-type", "").lower()
    if "image/png" not in content_type:
        raise ValueError("Xiaomi QR endpoint did not return a PNG image")
    return response.content


class MijiaAdapter:
    """Translate mijiaAPI calls and failures into stable application contracts."""

    def __init__(
        self,
        api_client: MijiaAPIClient | None = None,
        *,
        credential_store: WindowsCredentialStore | None = None,
        api_factory: Callable[[Path], MijiaAPIClient] = _default_api_factory,
        spec_loader: Callable[[str, Path], dict[str, Any]] = _default_spec_loader,
        qr_fetcher: Callable[[str], bytes] = _default_qr_fetcher,
        qr_directory: Path | None = None,
    ) -> None:
        self._credential_store = credential_store
        self._api_factory: Callable[[Path], MijiaAPIClient] | None = None
        self._spec_loader = spec_loader
        self._qr_fetcher = qr_fetcher
        self._pending_login_data: dict[str, Any] | None = None
        self._qr_path: Path | None = None
        if api_client is None:
            self._credential_store = credential_store or WindowsCredentialStore()
            auth_path = self._credential_store.prepare()
            self._api_factory = api_factory
            self._api = api_factory(auth_path)
        else:
            self._api = api_client
        self._qr_directory = qr_directory or (
            self._credential_store.working_directory
            if self._credential_store is not None
            else Path(self._api.auth_data_path).parent
        )

    def begin_login(self) -> Path | None:
        """Fetch a QR code into private temporary storage without waiting for a scan."""
        try:
            login_data = self._api._get_qr_login_data()
            if login_data.get("refreshed"):
                self._persist_credentials()
                logger.info("Mijia session refreshed; QR scan is not required")
                return None

            qr_data = self._qr_fetcher(str(login_data["qr"]))
            if not qr_data.startswith(b"\x89PNG\r\n\x1a\n"):
                raise ValueError("Xiaomi QR response is not a valid PNG")
            self._qr_directory.mkdir(parents=True, exist_ok=True)
            qr_path = self._qr_directory / "mijia-login-qr.png"
            qr_path.write_bytes(qr_data)
            self._qr_path = qr_path
            self._pending_login_data = login_data
            logger.info("Mijia login QR code is ready at %s", qr_path)
            return qr_path
        except Exception as error:
            raise self._translate(error, AuthenticationError, "无法生成米家登录二维码") from error

    def complete_login(self) -> None:
        """Wait for the user to scan the QR code prepared by :meth:`begin_login`."""
        if self._pending_login_data is None:
            return
        try:
            self._api._complete_qr_login(self._pending_login_data)
            self._persist_credentials()
            logger.info("Mijia login completed")
        except Exception as error:
            raise self._translate(error, AuthenticationError, "米家登录失败") from error
        finally:
            self._pending_login_data = None

    def login(self, qr_ready: Callable[[Path], None] | None = None) -> None:
        """Prepare a local QR image, notify the caller, and wait for confirmation."""
        qr_path = self.begin_login()
        if qr_path is not None:
            if qr_ready is not None:
                qr_ready(qr_path)
            self.complete_login()

    def is_authenticated(self) -> bool:
        """Check whether the stored session is accepted by Xiaomi cloud."""
        try:
            authenticated = bool(self._api.available)
            self._persist_credentials()
            return authenticated
        except Exception as error:
            raise self._translate(error, AuthenticationError, "无法验证米家登录状态") from error

    def has_stored_credentials(self) -> bool:
        """Return whether a persisted session exists without making a network request."""
        return self._credential_store is None or self._credential_store.exists

    def get_devices(self) -> list[dict[str, Any]]:
        """Return all devices visible to the authenticated account."""
        try:
            devices = self._api.get_devices_list()
            self._persist_credentials()
            logger.info("Loaded %d Mijia devices", len(devices))
            return devices
        except Exception as error:
            raise self._translate(error, NetworkError, "获取米家设备列表失败") from error

    def get_properties(
        self, requests: dict[str, Any] | list[dict[str, Any]]
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Read one or more MIoT properties."""
        try:
            result = self._api.get_devices_prop(requests)
            self._persist_credentials()
            self._ensure_success(result, PropertyReadError, "读取设备属性失败")
            return result
        except Exception as error:
            raise self._translate(error, PropertyReadError, "读取设备属性失败") from error

    def get_properties_batch(
        self,
        requests: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Read a batch while preserving per-property result codes for isolation."""
        try:
            result = self._api.get_devices_prop(requests)
            self._persist_credentials()
            return result if isinstance(result, list) else [result]
        except Exception as error:
            raise self._translate(error, PropertyReadError, "批量读取设备属性失败") from error

    def set_property(self, did: str, siid: int, piid: int, value: Any) -> dict[str, Any]:
        """Set one MIoT property by its stable numeric identifiers."""
        request = {"did": did, "siid": siid, "piid": piid, "value": value}
        try:
            result = self._api.set_devices_prop(request)
            self._persist_credentials()
            self._ensure_success(result, PropertyWriteError, "设置设备属性失败")
            logger.info("Set property: device=%s siid=%d piid=%d", did, siid, piid)
            return result
        except Exception as error:
            raise self._translate(error, PropertyWriteError, "设置设备属性失败") from error

    def run_action(
        self,
        did: str,
        siid: int,
        aiid: int,
        parameters: list[Any] | None = None,
    ) -> dict[str, Any]:
        """Execute one MIoT action by its stable numeric identifiers."""
        request: dict[str, Any] = {"did": did, "siid": siid, "aiid": aiid}
        if parameters is not None:
            request["value"] = parameters
        try:
            result = self._api.run_action(request)
            self._persist_credentials()
            self._ensure_success(result, ActionError, "执行设备 Action 失败")
            logger.info("Run action: device=%s siid=%d aiid=%d", did, siid, aiid)
            return result
        except Exception as error:
            raise self._translate(error, ActionError, "执行设备 Action 失败") from error

    def get_device_spec(self, model: str) -> dict[str, Any]:
        """Load the MIoT property/action description for a model."""
        try:
            cache_path = Path(self._api.auth_data_path).parent
            return self._spec_loader(model, cache_path)
        except Exception as error:
            raise self._translate(
                error, UnsupportedDeviceError, f"无法获取设备规格：{model}"
            ) from error

    def clear_credentials(self) -> None:
        """Remove stored and in-memory authentication material."""
        self._remove_qr_code()
        self._pending_login_data = None
        if self._credential_store is not None:
            self._credential_store.clear()
            if self._api_factory is not None:
                try:
                    self._api = self._api_factory(self._credential_store.prepare())
                except Exception as error:
                    raise AuthenticationError("无法重置米家登录状态") from error

    def close(self) -> None:
        """Persist refreshed credentials and remove their plaintext working copy."""
        self._persist_credentials()
        self._remove_qr_code()
        if self._credential_store is not None:
            self._credential_store.close()

    def _remove_qr_code(self) -> None:
        if self._qr_path is not None:
            self._qr_path.unlink(missing_ok=True)
        self._qr_path = None

    def _persist_credentials(self) -> None:
        if self._credential_store is not None:
            self._credential_store.persist()

    @staticmethod
    def _ensure_success(
        result: dict[str, Any] | list[dict[str, Any]],
        exception_type: type[MijiaDesktopError],
        message: str,
    ) -> None:
        results = result if isinstance(result, list) else [result]
        for item in results:
            code = int(item.get("code", 0))
            if code in (0, 1):
                continue
            if code in OFFLINE_CODES:
                raise DeviceOfflineError("设备离线或响应超时")
            raise exception_type(f"{message}（错误码 {code}）")

    @staticmethod
    def _translate(
        error: Exception,
        default_type: type[MijiaDesktopError],
        message: str,
    ) -> MijiaDesktopError:
        if isinstance(error, MijiaDesktopError):
            return error
        error_name = type(error).__name__
        if error_name == "LoginError":
            return AuthenticationError(message)
        if error_name in {"ConnectionError", "Timeout", "RequestException", "APIError"}:
            return NetworkError(message)
        return default_type(message)

    def __enter__(self) -> MijiaAdapter:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()
