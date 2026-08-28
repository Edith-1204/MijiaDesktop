"""Convert mijiaAPI dictionaries into stable device-domain models."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from app.models.action import DeviceAction
from app.models.capability import DeviceCapability


def normalize_name(name: str) -> str:
    return name.strip().lower().replace("_", "-")


def parse_capability(
    raw_property: Mapping[str, Any],
    value: Any = None,
) -> DeviceCapability:
    """Parse one mijiaAPI property description."""
    method = raw_property.get("method") or {}
    access = str(raw_property.get("rw") or "")
    value_range = raw_property.get("range") or []
    enum_values = {
        item.get("value"): str(
            item.get("desc_zh_cn") or item.get("description") or item.get("value")
        )
        for item in (raw_property.get("value-list") or [])
    }
    return DeviceCapability(
        name=normalize_name(str(raw_property.get("name") or "unknown")),
        description=str(raw_property.get("description") or raw_property.get("name") or ""),
        value_type=str(raw_property.get("type") or "unknown"),
        readable="r" in access,
        writable="w" in access,
        value=value,
        unit=raw_property.get("unit"),
        min_value=value_range[0] if len(value_range) >= 2 else None,
        max_value=value_range[1] if len(value_range) >= 2 else None,
        step=value_range[2] if len(value_range) >= 3 else None,
        enum_values=enum_values,
        siid=int(method.get("siid", 0)),
        piid=int(method.get("piid", 0)),
        metadata=dict(raw_property),
    )


def parse_action(raw_action: Mapping[str, Any]) -> DeviceAction:
    """Parse one mijiaAPI action description."""
    method = raw_action.get("method") or {}
    parameters = raw_action.get("parameters") or raw_action.get("in") or []
    return DeviceAction(
        name=normalize_name(str(raw_action.get("name") or "unknown")),
        description=str(raw_action.get("description") or raw_action.get("name") or ""),
        siid=int(method.get("siid", 0)),
        aiid=int(method.get("aiid", 0)),
        parameters=list(parameters),
        metadata=dict(raw_action),
    )


def extract_property_values(raw_device: Mapping[str, Any]) -> dict[str, Any]:
    """Extract any named property snapshot embedded in a device-list item."""
    raw_values = raw_device.get("prop") or raw_device.get("properties") or {}
    if isinstance(raw_values, str):
        try:
            raw_values = json.loads(raw_values)
        except json.JSONDecodeError:
            return {}
    if not isinstance(raw_values, Mapping):
        return {}
    return {normalize_name(str(name)): value for name, value in raw_values.items()}


def parse_capabilities(
    raw_properties: list[Mapping[str, Any]],
    values: Mapping[str, Any] | None = None,
) -> dict[str, DeviceCapability]:
    normalized_values = {
        normalize_name(str(name)): value for name, value in (values or {}).items()
    }
    capabilities: dict[str, DeviceCapability] = {}
    for raw_property in raw_properties:
        name = normalize_name(str(raw_property.get("name") or "unknown"))
        capability = parse_capability(raw_property, normalized_values.get(name))
        capabilities[name] = capability
    return capabilities


def parse_actions(raw_actions: list[Mapping[str, Any]]) -> dict[str, DeviceAction]:
    actions: dict[str, DeviceAction] = {}
    for raw_action in raw_actions:
        action = parse_action(raw_action)
        actions[action.name] = action
    return actions

