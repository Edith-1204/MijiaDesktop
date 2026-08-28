"""Thread-safe device state refresh and cache management."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from threading import Lock, RLock

from PySide6.QtCore import QObject, Signal

from app.core.device_manager import DeviceManager
from app.models.device import BaseDevice
from app.utils.logger import get_logger


logger = get_logger(__name__)


class StateManager(QObject):
    """Batch-refresh properties and expose immutable cache snapshots."""

    refresh_started = Signal()
    state_updated = Signal(object)
    refresh_failed = Signal(object)
    refresh_finished = Signal()

    def __init__(
        self,
        device_manager: DeviceManager,
        *,
        retry_count: int = 1,
        retry_delay: float = 0.25,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.device_manager = device_manager
        self.retry_count = max(0, retry_count)
        self.retry_delay = max(0.0, retry_delay)
        self._refresh_lock = Lock()
        self._cache_lock = RLock()
        self._cache: dict[str, dict[str, object]] = {}
        self._updated_at: datetime | None = None

    @property
    def updated_at(self) -> datetime | None:
        with self._cache_lock:
            return self._updated_at

    def seed(self, devices: tuple[BaseDevice, ...]) -> None:
        """Prime the cache from property values included in device discovery."""
        initial = {
            device.did: {
                capability.name: capability.value
                for capability in device.properties.values()
                if capability.value is not None
            }
            for device in devices
        }
        with self._cache_lock:
            self._cache = initial

    def refresh(
        self,
        dids: set[str] | None = None,
        capability_names: set[str] | None = None,
    ) -> dict[str, dict[str, object]]:
        """Refresh requested devices once, retrying transient failures as configured."""
        if not self._refresh_lock.acquire(blocking=False):
            logger.info("Skipped overlapping state refresh")
            return self.snapshot(dids)
        self.refresh_started.emit()
        try:
            last_error: Exception | None = None
            for attempt in range(self.retry_count + 1):
                try:
                    refreshed = self.device_manager.read_properties_batch(
                        dids,
                        capability_names=capability_names,
                    )
                    with self._cache_lock:
                        for did, values in refreshed.items():
                            self._cache.setdefault(did, {}).update(values)
                        self._updated_at = datetime.now(UTC)
                    snapshot = self.snapshot(dids)
                    self.state_updated.emit(snapshot)
                    return snapshot
                except Exception as error:
                    last_error = error
                    logger.warning(
                        "State refresh attempt %d/%d failed: %s",
                        attempt + 1,
                        self.retry_count + 1,
                        error,
                    )
                    if attempt < self.retry_count and self.retry_delay:
                        time.sleep(self.retry_delay)
            assert last_error is not None
            self.refresh_failed.emit(last_error)
            raise last_error
        finally:
            self._refresh_lock.release()
            self.refresh_finished.emit()

    def snapshot(self, dids: set[str] | None = None) -> dict[str, dict[str, object]]:
        """Return a copy so UI consumers cannot mutate the shared cache."""
        with self._cache_lock:
            return {
                did: dict(values)
                for did, values in self._cache.items()
                if dids is None or did in dids
            }
