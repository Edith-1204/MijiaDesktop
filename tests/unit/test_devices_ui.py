from app.models.capability import DeviceCapability
from app.models.device import BaseDevice, DeviceType
from app.ui.main_window import MainWindow
from app.ui.pages.favorites_page import FavoritesPage
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


def test_device_card_emits_favorite_change(qtbot):
    card = DeviceCard(make_device())
    qtbot.addWidget(card)
    requests = []
    card.favorite_requested.connect(
        lambda did, favorite: requests.append((did, favorite))
    )
    card.favorite_button.click()
    assert requests == [("light-1", True)]


def test_devices_page_filters_name_and_model(qtbot):
    page = DevicesPage()
    qtbot.addWidget(page)
    page.set_devices((make_device("light-1", "书房灯"), make_device("light-2", "卧室灯")))
    page.search_input.setText("书房")
    assert not page.cards["light-1"].isHidden()
    assert page.cards["light-2"].isHidden()


def test_devices_page_reuses_parented_cards_during_favorite_updates(qtbot):
    page = DevicesPage()
    qtbot.addWidget(page)
    device = make_device()
    page.set_devices((device,))
    original = page.cards[device.did]

    device.favorite = True
    page.set_devices((device,))

    assert page.cards[device.did] is original
    assert original.parentWidget() is page.scroll_content
    assert original.favorite_button.isChecked()


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

    @property
    def devices(self):
        return (self.device,)

    def read_properties_batch(self, dids=None, *, capability_names=None):
        self.calls.append(("read_properties_batch", dids, capability_names))
        return {self.device.did: {"on": self.device.primary_state}}

    def set_property(self, did, name, value):
        self.calls.append(("set_property", did, name, value))
        self.device.primary_state = value
        self.device.properties["on"].value = value
        return {"code": 0}

    def get_device(self, did):
        assert did == self.device.did
        return self.device

    def run_action(self, did, name, parameters=None):
        self.calls.append(("run_action", did, name, parameters))
        return {"code": 0}

    def set_favorite(self, did, favorite):
        self.calls.append(("set_favorite", did, favorite))
        self.device.favorite = favorite
        return self.device


def test_main_window_sync_and_switch_use_manager_in_background(qtbot):
    manager = FakeManager()
    window = MainWindow(manager, auto_refresh=True)
    qtbot.addWidget(window)
    qtbot.waitUntil(lambda: "light-1" in window.devices_page.cards)
    window.quick_switch("light-1", True)
    qtbot.waitUntil(lambda: len(manager.calls) == 3)
    qtbot.waitUntil(lambda: window.devices_page.cards["light-1"].state_label.text() == "ON")
    assert manager.calls == [
        ("sync_devices",),
        ("set_property", "light-1", "on", True),
        ("read_properties_batch", {"light-1"}, {"on"}),
    ]


def test_main_window_opens_detail_and_changes_generic_property(qtbot):
    manager = FakeManager()
    window = MainWindow(manager, auto_refresh=True)
    qtbot.addWidget(window)
    qtbot.waitUntil(lambda: "light-1" in window.devices_page.cards)
    window.open_device_detail("light-1")
    assert window.pages.currentWidget() is window.device_detail_page
    qtbot.waitUntil(lambda: len(manager.calls) == 2)

    window.change_property("light-1", "on", True)
    qtbot.waitUntil(lambda: len(manager.calls) == 4)
    qtbot.waitUntil(lambda: "状态已刷新" in window.device_detail_page.summary_label.text())

    assert manager.calls[-2:] == [
        ("set_property", "light-1", "on", True),
        ("read_properties_batch", {"light-1"}, {"on"}),
    ]


def test_main_window_runs_generic_action_through_manager(qtbot):
    manager = FakeManager()
    window = MainWindow(manager, auto_refresh=True)
    qtbot.addWidget(window)
    qtbot.waitUntil(lambda: "light-1" in window.devices_page.cards)
    window.open_device_detail("light-1")
    qtbot.waitUntil(lambda: len(manager.calls) == 2)

    window.run_device_action("light-1", "toggle")
    qtbot.waitUntil(lambda: len(manager.calls) == 4)
    qtbot.waitUntil(lambda: "状态已刷新" in window.device_detail_page.summary_label.text())

    assert manager.calls[-2:] == [
        ("run_action", "light-1", "toggle", None),
        ("read_properties_batch", {"light-1"}, None),
    ]


def test_main_window_manual_refresh_uses_state_manager_and_timer(qtbot):
    manager = FakeManager()
    window = MainWindow(manager, auto_refresh=True)
    qtbot.addWidget(window)
    qtbot.waitUntil(lambda: "light-1" in window.devices_page.cards)
    assert window.refresh_timer.interval() == 30_000
    assert window.refresh_timer.isActive()

    window.manual_refresh()
    qtbot.waitUntil(lambda: len(manager.calls) == 2)
    assert manager.calls[-1] == ("read_properties_batch", None, {"on"})
    assert window.devices_page.status_label.text().startswith("状态已刷新")


def test_favorites_page_filters_devices_and_main_window_updates_it(qtbot):
    page = FavoritesPage()
    qtbot.addWidget(page)
    favorite = make_device("light-1", "收藏灯")
    favorite.favorite = True
    page.set_devices((favorite, make_device("light-2", "普通灯")))
    assert set(page.cards) == {"light-1"}

    manager = FakeManager()
    window = MainWindow(manager, auto_refresh=True)
    qtbot.addWidget(window)
    qtbot.waitUntil(lambda: "light-1" in window.devices_page.cards)
    window.change_favorite("light-1", True)
    assert set(window.favorites_page.cards) == {"light-1"}
    assert manager.calls[-1] == ("set_favorite", "light-1", True)


def test_close_hides_window_when_tray_is_available(qtbot):
    window = MainWindow(auto_refresh=False, enable_tray=True)
    qtbot.addWidget(window)
    window.tray_service.available = True
    messages = []
    window.tray_service.show_hidden_message = lambda: messages.append(True)
    window.show()

    window.close()

    assert not window.isVisible()
    assert messages == [True]
    window._allow_exit = True
