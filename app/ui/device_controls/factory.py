"""Select focused controls by classified device family."""

from __future__ import annotations

from app.models.device import BaseDevice, DeviceType
from app.ui.device_controls.air_conditioner_control import AirConditionerControl
from app.ui.device_controls.fan_control import FanControl
from app.ui.device_controls.light_control import LightControl
from app.ui.device_controls.plug_control import PlugControl
from app.ui.device_controls.specialized_control import SpecializedDeviceControl


CONTROL_TYPES: dict[DeviceType, type[SpecializedDeviceControl]] = {
    DeviceType.LIGHT: LightControl,
    DeviceType.PLUG: PlugControl,
    DeviceType.FAN: FanControl,
    DeviceType.AIR_CONDITIONER: AirConditionerControl,
}


def create_specialized_control(device: BaseDevice) -> SpecializedDeviceControl | None:
    """Return a family-specific view without relying on device model strings."""
    control_type = CONTROL_TYPES.get(device.device_type)
    return control_type(device) if control_type is not None else None
