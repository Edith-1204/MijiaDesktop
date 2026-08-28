from PySide6.QtWidgets import QWidget

from app.models.capability import DeviceCapability
from app.models.device import BaseDevice, DeviceType
from app.services.tray_service import TrayService


def make_favorite(*, writable=True):
    return BaseDevice(
        did="light-1",
        name="收藏灯",
        model="test.light.v1",
        device_type=DeviceType.LIGHT,
        favorite=True,
        primary_state=False,
        properties={
            "on": DeviceCapability("on", "开关", "bool", True, writable, value=False),
        },
    )


def test_tray_lists_only_controllable_favorites(qtbot):
    window = QWidget()
    qtbot.addWidget(window)
    service = TrayService(window)
    requests = []
    service.quick_switch_requested.connect(
        lambda did, state: requests.append((did, state))
    )

    service.update_devices((make_favorite(), make_favorite(writable=False)))
    device_actions = [
        action for action in service.menu.actions() if action.text() == "★ 收藏灯"
    ]
    assert len(device_actions) == 1
    device_actions[0].trigger()
    assert requests == [("light-1", True)]


def test_tray_keeps_open_refresh_and_exit_commands(qtbot):
    window = QWidget()
    qtbot.addWidget(window)
    service = TrayService(window)
    service.update_devices(())
    texts = [action.text() for action in service.menu.actions()]
    assert "打开主界面" in texts
    assert "刷新设备" in texts
    assert "退出" in texts
