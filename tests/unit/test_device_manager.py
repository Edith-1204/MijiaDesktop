from app.core.device_manager import DeviceManager
from app.models.device import DeviceType


LIGHT_SPEC = {
    "name": "Test Light",
    "model": "test.light.v1",
    "properties": [
        {
            "name": "on",
            "description": "Switch",
            "type": "bool",
            "rw": "rw",
            "range": None,
            "method": {"siid": 2, "piid": 1},
        },
        {
            "name": "brightness",
            "description": "Brightness",
            "type": "uint",
            "rw": "rw",
            "range": [1, 100, 1],
            "method": {"siid": 2, "piid": 2},
        },
    ],
    "actions": [
        {"name": "toggle", "description": "Toggle", "method": {"siid": 2, "aiid": 1}}
    ],
}


class FakeAdapter:
    def __init__(self):
        self.calls = []

    def get_devices(self):
        return [
            {
                "did": "light-1",
                "name": "书房灯",
                "model": "test.light.v1",
                "isOnline": True,
                "prop": {"on": False, "brightness": 50},
            }
        ]

    def get_device_spec(self, model):
        self.calls.append(("get_device_spec", model))
        return LIGHT_SPEC

    def get_properties(self, request):
        self.calls.append(("get_properties", request))
        return {**request, "code": 0, "value": True}

    def set_property(self, did, siid, piid, value):
        self.calls.append(("set_property", did, siid, piid, value))
        return {"code": 0}

    def run_action(self, did, siid, aiid, parameters):
        self.calls.append(("run_action", did, siid, aiid, parameters))
        return {"code": 0}


def test_raw_device_is_converted_to_unified_model():
    adapter = FakeAdapter()
    manager = DeviceManager(adapter)

    devices = manager.sync_devices()
    device = devices[0]

    assert device.did == "light-1"
    assert device.device_type is DeviceType.LIGHT
    assert device.online is True
    assert device.primary_state is False
    assert device.properties["brightness"].value == 50
    assert device.actions["toggle"].aiid == 1


def test_device_operations_only_flow_through_adapter():
    adapter = FakeAdapter()
    manager = DeviceManager(adapter)
    manager.sync_devices()

    assert manager.read_property("light-1", "on") is True
    manager.set_property("light-1", "on", False)
    manager.run_action("light-1", "toggle")

    assert adapter.calls[-3:] == [
        ("get_properties", {"did": "light-1", "siid": 2, "piid": 1}),
        ("set_property", "light-1", 2, 1, False),
        ("run_action", "light-1", 2, 1, None),
    ]


def test_spec_is_cached_per_model():
    adapter = FakeAdapter()
    raw_devices = adapter.get_devices()
    raw_devices.append({**raw_devices[0], "did": "light-2", "name": "另一盏灯"})
    adapter.get_devices = lambda: raw_devices
    manager = DeviceManager(adapter)

    manager.sync_devices()

    assert adapter.calls.count(("get_device_spec", "test.light.v1")) == 1

