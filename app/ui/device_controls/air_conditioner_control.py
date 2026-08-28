"""Focused controls for air conditioners and AC companions."""

from app.ui.device_controls.specialized_control import SpecializedDeviceControl


class AirConditionerControl(SpecializedDeviceControl):
    title = "空调控制"
    description = "快速调整电源、运行模式、目标温度、风速和摆风。"
    capability_names = (
        "on",
        "mode",
        "target-temperature",
        "fan-level",
        "swing",
        "horizontal-swing",
        "vertical-swing",
    )
