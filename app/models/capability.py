"""Unified MIoT device capability model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class DeviceCapability:
    """A readable and/or writable property exposed by a device."""

    name: str
    description: str
    value_type: str
    readable: bool
    writable: bool
    value: Any = None
    unit: str | None = None
    min_value: int | float | None = None
    max_value: int | float | None = None
    step: int | float | None = None
    enum_values: dict[Any, str] = field(default_factory=dict)
    siid: int = 0
    piid: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def has_range(self) -> bool:
        return self.min_value is not None and self.max_value is not None

    @property
    def is_enum(self) -> bool:
        return bool(self.enum_values)

