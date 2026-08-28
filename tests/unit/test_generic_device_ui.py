import pytest

from app.models.action import DeviceAction
from app.models.capability import DeviceCapability
from app.models.device import BaseDevice
from app.ui.device_controls.generic_control import GenericDeviceControl
from app.ui.pages.device_detail_page import DeviceDetailPage
from app.ui.widgets.action_widget import ActionWidget
from app.ui.widgets.property_widget import (
    BooleanPropertyWidget,
    EnumPropertyWidget,
    NumberPropertyWidget,
    ReadOnlyPropertyWidget,
    SliderPropertyWidget,
    create_property_widget,
)


def capability(name, value_type, *, writable=True, value=None, value_range=None, enum=None):
    value_range = value_range or (None, None, None)
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
        enum_values=enum or {},
        siid=2,
        piid=1,
    )


@pytest.mark.parametrize(
    ("item", "expected_type"),
    [
        (capability("on", "bool", value=False), BooleanPropertyWidget),
        (capability("brightness", "uint", value=50, value_range=(1, 100, 1)), SliderPropertyWidget),
        (capability("count", "int", value=2), NumberPropertyWidget),
        (capability("mode", "uint", value=1, enum={1: "自动", 2: "手动"}), EnumPropertyWidget),
        (capability("temperature", "float", writable=False, value=24.5), ReadOnlyPropertyWidget),
    ],
)
def test_widget_factory_maps_capability_shape(item, expected_type, qapp):
    assert isinstance(create_property_widget(item), expected_type)


def make_generic_device():
    properties = {
        "on": capability("on", "bool", value=False),
        "brightness": capability("brightness", "uint", value=50, value_range=(1, 100, 1)),
        "mode": capability("mode", "uint", value=1, enum={1: "自动", 2: "手动"}),
        "temperature": capability("temperature", "float", writable=False, value=24.5),
    }
    return BaseDevice(
        did="unknown-1",
        name="未知设备",
        model="vendor.unknown.v1",
        online=True,
        properties=properties,
        actions={"toggle": DeviceAction("toggle", "切换", 2, 1)},
    )


def test_generic_control_builds_properties_and_actions(qtbot):
    control = GenericDeviceControl(make_generic_device())
    qtbot.addWidget(control)
    assert set(control.property_widgets) == {"on", "brightness", "mode", "temperature"}
    assert set(control.action_widgets) == {"toggle"}


def test_boolean_control_emits_change_and_rolls_back(qtbot):
    widget = BooleanPropertyWidget(capability("on", "bool", value=False))
    qtbot.addWidget(widget)
    assert widget.editor.text() == "关闭"
    changes = []
    widget.change_requested.connect(lambda name, value: changes.append((name, value)))
    widget.editor.click()
    assert changes == [("on", True)]
    assert not widget.editor.isEnabled()
    widget.finish(False)
    assert not widget.editor.isChecked()
    assert widget.editor.text() == "关闭"
    assert widget.editor.isEnabled()


def test_slider_preserves_zero_upper_bound(qtbot):
    widget = SliderPropertyWidget(
        capability("offset", "int", value=-5, value_range=(-10, 0, 1))
    )
    qtbot.addWidget(widget)
    assert widget.editor.minimum() == -10
    assert widget.editor.maximum() == 0


def test_action_widget_emits_no_parameter_action(qtbot):
    widget = ActionWidget(DeviceAction("toggle", "切换", 2, 1))
    qtbot.addWidget(widget)
    actions = []
    widget.action_requested.connect(actions.append)
    widget.button.click()
    assert actions == ["toggle"]


def test_device_detail_page_wraps_device_identity_in_signals(qtbot):
    page = DeviceDetailPage()
    qtbot.addWidget(page)
    device = make_generic_device()
    page.set_device(device)
    changes = []
    page.property_change_requested.connect(
        lambda did, name, value: changes.append((did, name, value))
    )
    boolean = page.generic_control.property_widgets["on"]
    boolean.editor.click()
    assert page.name_label.text() == "未知设备"
    assert changes == [("unknown-1", "on", True)]
