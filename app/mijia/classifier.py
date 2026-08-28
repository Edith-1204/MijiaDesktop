"""Capability-first device type classification."""

from __future__ import annotations

from collections.abc import Iterable

from app.models.device import DeviceType


class DeviceClassifier:
    """Classify broad device families without exact-model allowlists."""

    _MODEL_HINTS: tuple[tuple[DeviceType, tuple[str, ...]], ...] = (
        (DeviceType.AIR_CONDITIONER, ("aircondition", "air-condition", "acpartner")),
        (DeviceType.HUMIDIFIER, ("humidifier",)),
        (DeviceType.PURIFIER, ("airpurifier", "purifier")),
        (DeviceType.VACUUM, ("vacuum", "sweeper")),
        (DeviceType.CURTAIN, ("curtain",)),
        (DeviceType.CAMERA, ("camera", "chuangmi")),
        (DeviceType.FAN, (".fan.", "fan-")),
        (DeviceType.LIGHT, (".light.", "light-")),
        (DeviceType.PLUG, (".plug.", "outlet", "socket")),
        (DeviceType.SENSOR, (".sensor", "sensor-")),
    )
    _OTHER_MODEL_HINTS = (
        ".oven.",
        ".ihcooker.",
        ".kettle.",
        ".washer.",
        ".waterpuri.",
        ".wifispeaker.",
        ".tv.",
        ".lock.",
        ".scales.",
    )

    def classify(
        self,
        model: str,
        property_names: Iterable[str] = (),
        action_names: Iterable[str] = (),
        *,
        spec_name: str = "",
    ) -> DeviceType:
        properties = {name.lower().replace("_", "-") for name in property_names}
        actions = {name.lower().replace("_", "-") for name in action_names}
        searchable = f"{model} {spec_name}".lower()

        # Broad but explicit model-family hints are stronger than overlapping
        # capabilities such as filter life, fan level, or target temperature.
        for device_type, hints in self._MODEL_HINTS:
            if any(hint in searchable for hint in hints):
                return device_type
        if any(hint in searchable for hint in self._OTHER_MODEL_HINTS):
            return DeviceType.OTHER

        if {"target-temperature", "fan-level"} <= properties or (
            "target-temperature" in properties and "mode" in properties
        ):
            return DeviceType.AIR_CONDITIONER
        if "humidity" in properties and "target-humidity" in properties:
            return DeviceType.HUMIDIFIER
        if any(name in properties for name in {"pm2.5-density", "filter-life-level"}):
            return DeviceType.PURIFIER
        if any(name in properties for name in {"status", "brush-life-level"}) and any(
            "clean" in name or "sweep" in name for name in actions
        ):
            return DeviceType.VACUUM
        if any(name in properties for name in {"motor-control", "current-position"}):
            return DeviceType.CURTAIN
        if any(name in properties for name in {"horizontal-swing", "vertical-swing"}):
            return DeviceType.FAN
        if any(name in properties for name in {"brightness", "color-temperature", "color"}):
            return DeviceType.LIGHT
        if any(
            name in properties
            for name in {"electric-current", "electric-power", "power-consumption", "voltage"}
        ):
            return DeviceType.PLUG

        return DeviceType.OTHER
