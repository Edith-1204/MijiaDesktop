from app.core.state_manager import StateManager
from app.models.capability import DeviceCapability
from app.models.device import BaseDevice


def make_device():
    return BaseDevice(
        did="device-1",
        name="设备",
        model="test.device.v1",
        properties={
            "on": DeviceCapability("on", "开关", "bool", True, True, value=False),
        },
    )


class FakeDeviceManager:
    def __init__(self, *, failures=0):
        self.device = make_device()
        self.failures = failures
        self.calls = 0

    def read_properties_batch(self, dids=None, *, capability_names=None):
        self.calls += 1
        if self.calls <= self.failures:
            raise RuntimeError("temporary failure")
        self.device.properties["on"].value = True
        self.device.primary_state = True
        return {"device-1": {"on": True}}


def test_state_manager_seeds_and_returns_isolated_snapshot(qapp):
    manager = FakeDeviceManager()
    states = StateManager(manager, retry_delay=0)
    states.seed((manager.device,))

    snapshot = states.snapshot()
    snapshot["device-1"]["on"] = True

    assert states.snapshot() == {"device-1": {"on": False}}


def test_state_manager_refreshes_cache_and_emits_notification(qapp):
    manager = FakeDeviceManager()
    states = StateManager(manager, retry_delay=0)
    updates = []
    states.state_updated.connect(updates.append)

    result = states.refresh({"device-1"}, {"on"})

    assert result == {"device-1": {"on": True}}
    assert updates == [result]
    assert states.updated_at is not None


def test_state_manager_retries_and_reports_final_failure(qapp):
    recovering = FakeDeviceManager(failures=1)
    states = StateManager(recovering, retry_count=1, retry_delay=0)
    assert states.refresh() == {"device-1": {"on": True}}
    assert recovering.calls == 2

    failing = FakeDeviceManager(failures=2)
    states = StateManager(failing, retry_count=1, retry_delay=0)
    failures = []
    states.refresh_failed.connect(failures.append)
    try:
        states.refresh()
    except RuntimeError as error:
        assert str(error) == "temporary failure"
    else:
        raise AssertionError("refresh should fail after retries")
    assert len(failures) == 1
