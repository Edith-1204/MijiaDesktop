"""Unified MIoT device action model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class DeviceAction:
    """An invokable action exposed by a device."""

    name: str
    description: str
    siid: int
    aiid: int
    parameters: list[Any] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

