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
from app.mijia.adapter import MijiaAdapter
from app.mijia.classifier import DeviceClassifier
from app.mijia.parser import (
    extract_property_values,
    parse_actions,
    parse_capabilities,
)
from app.models.device import BaseDevice
from app.utils.logger import get_logger


logger = get_logger(__name__)


class DeviceManager:
    """Create unified models and act as the sole device-operation service."""

    def __init__(
        self,
        adapter: MijiaAdapter,
        classifier: DeviceClassifier | None = None,
    ) -> None:
        self._adapter = adapter
        self._classifier = classifier or DeviceClassifier()
        self._devices: dict[str, BaseDevice] = {}
        self._spec_cache: dict[str, dict[str, Any]] = {}

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
            try:
                self._spec_cache[model] = self._adapter.get_device_spec(model)
            except UnsupportedDeviceError as error:
                logger.warning("Device spec unavailable for model=%s: %s", model, error)
                self._spec_cache[model] = {}
        return self._spec_cache[model]

