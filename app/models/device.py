"""Unified Mijia device model."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from app.models.action import DeviceAction
from app.models.capability import DeviceCapability


class DeviceType(StrEnum):
    LIGHT = "light"
    FAN = "fan"
    AIR_CONDITIONER = "air_conditioner"
    PLUG = "plug"
    SENSOR = "sensor"
    CURTAIN = "curtain"
    PURIFIER = "purifier"
    HUMIDIFIER = "humidifier"
    VACUUM = "vacuum"
    CAMERA = "camera"
    OTHER = "other"


@dataclass(slots=True)
class BaseDevice:
    """Application-facing representation independent of mijiaAPI classes."""

    did: str
    name: str
    model: str
    device_type: DeviceType = DeviceType.OTHER
    online: bool = False
    favorite: bool = False
    properties: dict[str, DeviceCapability] = field(default_factory=dict)
    actions: dict[str, DeviceAction] = field(default_factory=dict)
    primary_state: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def capability(self, name: str) -> DeviceCapability | None:
        """Find a capability using MIoT dash/underscore normalization."""
        normalized = name.strip().lower().replace("_", "-")
        direct = self.properties.get(normalized)
        if direct is not None:
            return direct
        if normalized == "on":
            on_variants = sorted(
                (
                    capability
                    for capability in self.properties.values()
                    if capability.name.lower().replace("_", "-").startswith("on-")
                ),
                key=lambda capability: (not capability.writable, capability.siid, capability.piid),
            )
            if on_variants:
                return on_variants[0]
        return next(
            (
                capability
                for capability in self.properties.values()
                if capability.name.lower().replace("_", "-") == normalized
            ),
            None,
        )

    def action(self, name: str) -> DeviceAction | None:
        normalized = name.strip().lower().replace("_", "-")
        direct = self.actions.get(normalized)
        if direct is not None:
            return direct
        return next(
            (
                action
                for action in self.actions.values()
                if action.name.lower().replace("_", "-") == normalized
            ),
            None,
        )
