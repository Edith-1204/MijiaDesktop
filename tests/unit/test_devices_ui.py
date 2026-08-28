from app.models.capability import DeviceCapability
from app.models.device import BaseDevice, DeviceType
from app.ui.main_window import MainWindow
from app.ui.pages.devices_page import DevicesPage
from app.ui.widgets.device_card import DeviceCard


def make_device(did="light-1", name="书房灯", state=False):
    return BaseDevice(
        did=did,
        name=name,
        model="test.light.v1",
        device_type=DeviceType.LIGHT,
        online=True,
        primary_state=state,
        properties={
            "on": DeviceCapability(
                name="on",
                description="Switch",
                value_type="bool",
                readable=True,
                writable=True,
                value=state,
                siid=2,
                piid=1,
            )
        },
    )


def test_device_card_shows_state_and_emits_quick_switch(qtbot):
    card = DeviceCard(make_device())
    qtbot.addWidget(card)
    requests = []
    card.quick_switch_requested.connect(lambda did, state: requests.append((did, state)))
    assert card.name_label.text() == "书房灯"
    assert card.state_label.text() == "OFF"
    card.quick_button.click()
    assert requests == [("light-1", True)]


def test_devices_page_filters_name_and_model(qtbot):
    page = DevicesPage()
    qtbot.addWidget(page)
    page.set_devices((make_device("light-1", "书房灯"), make_device("light-2", "卧室灯")))
    page.search_input.setText("书房")
    assert not page.cards["light-1"].isHidden()
    assert page.cards["light-2"].isHidden()


def test_main_window_contains_devices_navigation(qtbot):
    window = MainWindow(auto_refresh=False)
    qtbot.addWidget(window)
    assert window.windowTitle() == "Mijia Desktop"
    assert window.devices_button.isChecked()
    assert window.pages.currentWidget() is window.devices_page


class FakeManager:
    def __init__(self):
        self.device = make_device()
        self.calls = []

    def sync_devices(self):
        self.calls.append(("sync_devices",))
        return (self.device,)

    def set_property(self, did, name, value):
        self.calls.append(("set_property", did, name, value))
        self.device.primary_state = value
        self.device.properties["on"].value = value
        return {"code": 0}


def test_main_window_sync_and_switch_use_manager_in_background(qtbot):
    manager = FakeManager()
    window = MainWindow(manager, auto_refresh=True)
    qtbot.addWidget(window)
    qtbot.waitUntil(lambda: "light-1" in window.devices_page.cards)
    window.quick_switch("light-1", True)
    qtbot.waitUntil(lambda: len(manager.calls) == 2)
    qtbot.waitUntil(lambda: window.devices_page.cards["light-1"].state_label.text() == "ON")
    assert manager.calls == [
        ("sync_devices",),
        ("set_property", "light-1", "on", True),
    ]

