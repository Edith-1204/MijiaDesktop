"""Device lifecycle and operation entry point."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.core.exceptions import (
    DeviceNotFoundError,
    PropertyReadError,
    PropertyWriteError,
    UnsupportedDeviceError,
)
from app.mijia.adapter import OFFLINE_CODES, MijiaAdapter
from app.mijia.classifier import DeviceClassifier
from app.mijia.parser import (
    extract_property_values,
    parse_actions,
    parse_capabilities,
)
from app.models.capability import DeviceCapability
from app.models.device import BaseDevice
from app.storage.repository import FavoritesRepository
from app.storage.spec_cache import DeviceSpecCache
from app.utils.logger import get_logger


logger = get_logger(__name__)


class DeviceManager:
    """Create unified models and act as the sole device-operation service."""

    def __init__(
        self,
        adapter: MijiaAdapter,
        classifier: DeviceClassifier | None = None,
        favorites_repository: FavoritesRepository | None = None,
        spec_cache: DeviceSpecCache | None = None,
    ) -> None:
        self._adapter = adapter
        self._classifier = classifier or DeviceClassifier()
        self._favorites_repository = favorites_repository
        self._persistent_spec_cache = spec_cache
        self._favorite_dids = (
            favorites_repository.list_dids()
            if favorites_repository is not None
            else set()
        )
        self._devices: dict[str, BaseDevice] = {}
        self._spec_cache: dict[str, dict[str, Any]] = {}
        self._pending_models: set[str] = set()

    @property
    def devices(self) -> tuple[BaseDevice, ...]:
        return tuple(
            sorted(self._devices.values(), key=lambda device: (not device.favorite, device.name))
        )

    def sync_devices(self) -> tuple[BaseDevice, ...]:
        """Fetch all raw devices and convert every item into a BaseDevice."""
        converted: dict[str, BaseDevice] = {}
        for raw_device in self._adapter.get_devices():
            model = str(raw_device.get("model") or "")
            spec = self._load_spec(model)
            device = self.create_device(raw_device, spec)
            converted[device.did] = device
        self._devices = converted
        logger.info("Converted %d devices into unified models", len(converted))
        return self.devices

    @property
    def needs_enrichment(self) -> bool:
        return bool(self._pending_models)

    def sync_devices_fast(self) -> tuple[BaseDevice, ...]:
        """Display devices immediately using only already-cached specifications."""
        converted: dict[str, BaseDevice] = {}
        pending: set[str] = set()
        for raw_device in self._adapter.get_devices():
            model = str(raw_device.get("model") or "")
            spec = self._get_cached_spec(model)
            if model and spec is None:
                pending.add(model)
            device = self.create_device(raw_device, spec or {})
            converted[device.did] = device
        self._devices = converted
        self._pending_models = pending
        logger.info(
            "Displayed %d devices; %d models require background enrichment",
            len(converted),
            len(pending),
        )
        return self.devices

    def enrich_devices(self) -> tuple[BaseDevice, ...]:
        """Fetch missing specifications and replace provisional device models."""
        converted: dict[str, BaseDevice] = {}
        for device in self.devices:
            raw_device = device.metadata.get("raw_device") or {}
            spec = self._load_spec(device.model)
            enriched = self.create_device(raw_device, spec)
            enriched.favorite = device.favorite
            converted[enriched.did] = enriched
        self._devices = converted
        self._pending_models.clear()
        logger.info("Finished background capability enrichment for %d devices", len(converted))
        return self.devices

    def create_device(
        self,
        raw_device: Mapping[str, Any],
        raw_spec: Mapping[str, Any] | None = None,
    ) -> BaseDevice:
        """Convert one mijiaAPI device-list item and optional spec."""
        spec = raw_spec or {}
        values = extract_property_values(raw_device)
        properties = parse_capabilities(list(spec.get("properties") or []), values)
        actions = parse_actions(list(spec.get("actions") or []))
        device_type = self._classifier.classify(
            str(raw_device.get("model") or ""),
            properties,
            actions,
            spec_name=str(spec.get("name") or ""),
        )
        primary_capability = next(
            (
                capability
                for name, capability in properties.items()
                if name == "on" or name.startswith("on-")
            ),
            None,
        )
        online_value = raw_device.get("online", raw_device.get("isOnline", False))
        return BaseDevice(
            did=str(raw_device.get("did") or ""),
            name=str(raw_device.get("name") or spec.get("name") or "未命名设备"),
            model=str(raw_device.get("model") or spec.get("model") or ""),
            device_type=device_type,
            online=bool(online_value),
            favorite=str(raw_device.get("did") or "") in self._favorite_dids,
            properties=properties,
            actions=actions,
            primary_state=primary_capability.value if primary_capability else None,
            metadata={"raw_device": dict(raw_device), "spec": dict(spec)},
        )

    def get_device(self, did: str) -> BaseDevice:
        try:
            return self._devices[did]
        except KeyError as error:
            raise DeviceNotFoundError(f"未找到设备：{did}") from error

    def set_favorite(self, did: str, favorite: bool) -> BaseDevice:
        device = self.get_device(did)
        if self._favorites_repository is not None:
            self._favorites_repository.set_favorite(did, favorite)
        if favorite:
            self._favorite_dids.add(did)
        else:
            self._favorite_dids.discard(did)
        device.favorite = favorite
        return device

    def read_property(self, did: str, capability_name: str) -> Any:
        device = self.get_device(did)
        capability = device.capability(capability_name)
        if capability is None or not capability.readable:
            raise PropertyReadError(f"设备不支持读取属性：{capability_name}")
        result = self._adapter.get_properties(
            {"did": did, "siid": capability.siid, "piid": capability.piid}
        )
        value = result.get("value")
        capability.value = value
        if capability.name == "on" or capability.name.startswith("on-"):
            device.primary_state = value
        return value

    def read_properties_batch(
        self,
        dids: set[str] | None = None,
        *,
        capability_names: set[str] | None = None,
        batch_size: int = 50,
    ) -> dict[str, dict[str, Any]]:
        """Read all readable capabilities in bounded cloud batches."""
        if batch_size < 1:
            raise ValueError("batch_size must be at least 1")
        requested: list[tuple[BaseDevice, DeviceCapability]] = []
        for device in self.devices:
            if dids is not None and device.did not in dids:
                continue
            requested.extend(
                (device, capability)
                for capability in device.properties.values()
                if capability.readable
                and capability.siid
                and capability.piid
                and (
                    capability_names is None
                    or any(
                        device.capability(name) is capability
                        for name in capability_names
                    )
                )
            )

        refreshed: dict[str, dict[str, Any]] = {}
        offline_dids: set[str] = set()
        for offset in range(0, len(requested), batch_size):
            group = requested[offset : offset + batch_size]
            partial = self._read_property_group(group, offline_dids)
            for did, values in partial.items():
                refreshed.setdefault(did, {}).update(values)
        return refreshed

    def _read_property_group(
        self,
        group: list[tuple[BaseDevice, DeviceCapability]],
        offline_dids: set[str],
    ) -> dict[str, dict[str, Any]]:
        group = [item for item in group if item[0].did not in offline_dids]
        if not group:
            return {}
        payload = [
            {"did": device.did, "siid": capability.siid, "piid": capability.piid}
            for device, capability in group
        ]
        batch_reader = getattr(self._adapter, "get_properties_batch", None)
        if batch_reader is None:
            raw_results = self._adapter.get_properties(payload)
            results = raw_results if isinstance(raw_results, list) else [raw_results]
        else:
            results = batch_reader(payload)
        by_key = {
            (device.did, capability.siid, capability.piid): (device, capability)
            for device, capability in group
        }
        refreshed: dict[str, dict[str, Any]] = {}
        for index, result in enumerate(results):
            fallback = group[index] if index < len(group) else None
            key = (
                str(result.get("did") or ""),
                int(result.get("siid") or 0),
                int(result.get("piid") or 0),
            )
            matched = by_key.get(key, fallback)
            if matched is None:
                continue
            device, capability = matched
            code = int(result.get("code", 0))
            if code not in (0, 1):
                if code in OFFLINE_CODES:
                    device.online = False
                    offline_dids.add(device.did)
                logger.warning(
                    "Skipped unreadable property: device=%s property=%s code=%d",
                    device.name,
                    capability.name,
                    code,
                )
                continue
            value = result.get("value")
            device.online = True
            capability.value = value
            refreshed.setdefault(device.did, {})[capability.name] = value
            if capability.name == "on" or capability.name.startswith("on-"):
                device.primary_state = value
        return refreshed

    def set_property(self, did: str, capability_name: str, value: Any) -> Any:
        device = self.get_device(did)
        capability = device.capability(capability_name)
        if capability is None or not capability.writable:
            raise PropertyWriteError(f"设备不支持写入属性：{capability_name}")
        result = self._adapter.set_property(
            did, capability.siid, capability.piid, value
        )
        capability.value = value
        if capability.name == "on" or capability.name.startswith("on-"):
            device.primary_state = value
        return result

    def run_action(
        self,
        did: str,
        action_name: str,
        parameters: list[Any] | None = None,
    ) -> Any:
        device = self.get_device(did)
        action = device.action(action_name)
        if action is None:
            raise UnsupportedDeviceError(f"设备不支持 Action：{action_name}")
        return self._adapter.run_action(
            did, action.siid, action.aiid, parameters
        )

    def _load_spec(self, model: str) -> dict[str, Any]:
        if not model:
            return {}
        if model not in self._spec_cache:
            cached = self._get_cached_spec(model)
            if cached is not None:
                return cached
            try:
                self._spec_cache[model] = self._adapter.get_device_spec(model)
            except UnsupportedDeviceError as error:
                logger.warning("Device spec unavailable for model=%s: %s", model, error)
                self._spec_cache[model] = {}
            if self._persistent_spec_cache is not None:
                self._persistent_spec_cache.put(model, self._spec_cache[model])
        return self._spec_cache[model]

    def _get_cached_spec(self, model: str) -> dict[str, Any] | None:
        if not model:
            return {}
        if model in self._spec_cache:
            return self._spec_cache[model]
        if self._persistent_spec_cache is None:
            return None
        cached = self._persistent_spec_cache.get(model)
        if cached is not None:
            self._spec_cache[model] = cached
        return cached
