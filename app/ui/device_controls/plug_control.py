"""Focused controls and readings for smart plugs."""

from app.ui.device_controls.specialized_control import SpecializedDeviceControl


class PlugControl(SpecializedDeviceControl):
    title = "插座控制"
    description = "控制电源，并查看设备提供的实时电气数据。"
    capability_names = (
        "on",
        "electric-power",
        "voltage",
        "electric-current",
        "power-consumption",
    )
