"""Focused controls for fans."""

from app.ui.device_controls.specialized_control import SpecializedDeviceControl


class FanControl(SpecializedDeviceControl):
    title = "风扇控制"
    description = "快速调整电源、风速、模式和摆风。"
    capability_names = (
        "on",
        "fan-level",
        "mode",
        "horizontal-swing",
        "vertical-swing",
        "angle",
    )
