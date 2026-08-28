import pytest

from app.models.action import DeviceAction
from app.models.capability import DeviceCapability
from app.models.device import BaseDevice, DeviceType
from app.ui.device_controls.air_conditioner_control import AirConditionerControl
from app.ui.device_controls.factory import create_specialized_control
from app.ui.device_controls.fan_control import FanControl
from app.ui.device_controls.light_control import ColorPropertyWidget, LightControl
from app.ui.device_controls.plug_control import PlugControl
from app.ui.pages.device_detail_page import DeviceDetailPage


def capability(name, *, writable=True):
    if name in {"on", "horizontal-swing", "vertical-swing", "swing"}:
        value_type, value = "bool", False
        value_range, enum = (None, None, None), {}
    elif name in {"mode", "fan-level"}:
        value_type, value = "uint", 1
        value_range, enum = (None, None, None), {1: "自动", 2: "强力"}
    else:
        value_type, value = "uint", 50
        value_range, enum = (1, 100, 1), {}
    return DeviceCapability(
        name=name,
        description=name,
        value_type=value_type,
        readable=True,
        writable=writable,
        value=value,
        min_value=value_range[0],
        max_value=value_range[1],
        step=value_range[2],
        enum_values=enum,
        siid=2,
        piid=1,
    )


def device(device_type, names):
    return BaseDevice(
        did=f"{device_type.value}-1",
        name=f"Test {device_type.value}",
        model="vendor.capability.device",
        device_type=device_type,
        online=True,
        properties={name: capability(name) for name in names},
        actions={"toggle": DeviceAction("toggle", "切换", 2, 1)},
    )


@pytest.mark.parametrize(
    ("device_type", "control_type", "names"),
    [
        (
            DeviceType.LIGHT,
            LightControl,
            ("on", "brightness", "color-temperature", "color", "mode"),
        ),
        (
            DeviceType.PLUG,
            PlugControl,
            ("on", "electric-power", "voltage", "electric-current", "power-consumption"),
        ),
        (
            DeviceType.FAN,
            FanControl,
            ("on", "fan-level", "mode", "horizontal-swing", "vertical-swing", "angle"),
        ),
        (
            DeviceType.AIR_CONDITIONER,
            AirConditionerControl,
            ("on", "mode", "target-temperature", "fan-level", "swing"),
        ),
    ],
)
def test_specialized_factory_uses_family_and_keeps_planned_order(
    device_type, control_type, names, qtbot
):
    control = create_specialized_control(device(device_type, names))
    qtbot.addWidget(control)
    assert isinstance(control, control_type)
    assert tuple(control.property_widgets) == names


def test_specialized_control_hides_unsupported_capabilities(qtbot):
    control = create_specialized_control(device(DeviceType.FAN, ("on",)))
    qtbot.addWidget(control)
    assert tuple(control.property_widgets) == ("on",)


def test_light_color_uses_color_picker_and_applies_confirmed_value(qtbot):
    control = create_specialized_control(device(DeviceType.LIGHT, ("color",)))
    qtbot.addWidget(control)
    widget = control.property_widgets["color"]
    assert isinstance(widget, ColorPropertyWidget)

    widget.finish(True, 0x336699)
    assert widget.editor.text() == "#336699"
    assert widget.capability.value == 0x336699


def test_other_device_has_no_specialized_control():
    assert create_specialized_control(device(DeviceType.OTHER, ("on",))) is None


def test_detail_page_separates_common_properties_actions_and_info(qtbot):
    page = DeviceDetailPage()
    qtbot.addWidget(page)
    light = device(DeviceType.LIGHT, ("on", "brightness"))
    page.set_device(light)

    assert [page.tabs.tabText(index) for index in range(page.tabs.count())] == [
        "常用控制",
        "全部属性",
        "Actions",
        "设备信息",
    ]
    assert page.tabs.isTabVisible(0)
    assert isinstance(page.specialized_control, LightControl)
    assert set(page.generic_control.property_widgets) == {"on", "brightness"}
    assert set(page.action_control.action_widgets) == {"toggle"}


def test_detail_page_keeps_common_and_full_property_values_in_sync(qtbot):
    page = DeviceDetailPage()
    qtbot.addWidget(page)
    page.set_device(device(DeviceType.LIGHT, ("on",)))
    common = page.specialized_control.property_widgets["on"]
    complete = page.generic_control.property_widgets["on"]

    common.editor.click()
    page.begin_property_update("on")
    assert not common.editor.isEnabled()
    assert not complete.editor.isEnabled()

    page.finish_property_update("on", True, value=True)
    assert common.editor.isChecked()
    assert complete.editor.isChecked()
    assert common.editor.isEnabled()
    assert complete.editor.isEnabled()


def test_detail_page_hides_common_tab_for_unknown_device(qtbot):
    page = DeviceDetailPage()
    qtbot.addWidget(page)
    page.set_device(device(DeviceType.LIGHT, ("on",)))
    previous = page.common_scroll.widget()
    page.set_device(device(DeviceType.OTHER, ("on",)))
    assert not page.tabs.isTabVisible(0)
    assert page.tabs.currentIndex() == 1
    assert page.common_scroll.widget() is None
    assert previous is not page.specialized_control
