"""Compact device summary and quick-control card."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout

from app.models.device import BaseDevice, DeviceType


DEVICE_ICONS = {
    DeviceType.LIGHT: "💡",
    DeviceType.FAN: "🌀",
    DeviceType.AIR_CONDITIONER: "❄",
    DeviceType.PLUG: "🔌",
    DeviceType.SENSOR: "◉",
    DeviceType.CURTAIN: "▥",
    DeviceType.PURIFIER: "✦",
    DeviceType.HUMIDIFIER: "💧",
    DeviceType.VACUUM: "●",
    DeviceType.CAMERA: "◉",
    DeviceType.OTHER: "◇",
}


class DeviceCard(QFrame):
    """Display one BaseDevice without knowing anything about mijiaAPI."""

    quick_switch_requested = Signal(str, bool)

    def __init__(self, device: BaseDevice, parent=None) -> None:
        super().__init__(parent)
        self.device = device
        self._pending = False
        self.setObjectName("deviceCard")
        self.setMinimumSize(250, 180)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(10)

        heading = QHBoxLayout()
        self.icon_label = QLabel()
        self.icon_label.setObjectName("deviceIcon")
        self.name_label = QLabel()
        self.name_label.setObjectName("deviceName")
        self.name_label.setWordWrap(True)
        heading.addWidget(self.icon_label)
        heading.addWidget(self.name_label, 1)
        root.addLayout(heading)

        self.model_label = QLabel()
        self.model_label.setObjectName("deviceModel")
        self.model_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        root.addWidget(self.model_label)

        status_row = QHBoxLayout()
        self.online_label = QLabel()
        self.online_label.setObjectName("onlineStatus")
        self.state_label = QLabel()
        self.state_label.setObjectName("primaryState")
        status_row.addWidget(self.online_label)
        status_row.addStretch(1)
        status_row.addWidget(self.state_label)
        root.addLayout(status_row)

        root.addStretch(1)
        self.quick_button = QPushButton()
        self.quick_button.setObjectName("quickSwitch")
        self.quick_button.setCheckable(True)
        self.quick_button.clicked.connect(self._request_quick_switch)
        root.addWidget(self.quick_button)

        self.update_device(device)

    @property
    def has_quick_switch(self) -> bool:
        capability = self.device.capability("on")
        return capability is not None and capability.writable

    def update_device(self, device: BaseDevice) -> None:
        self.device = device
        self.icon_label.setText(DEVICE_ICONS.get(device.device_type, "◇"))
        self.name_label.setText(device.name)
        self.model_label.setText(device.model or "未知型号")
        self.online_label.setText("● 在线" if device.online else "○ 离线/未知")
        self.online_label.setProperty("online", device.online)

        state = device.primary_state
        if isinstance(state, bool):
            self.state_label.setText("ON" if state else "OFF")
            self.quick_button.setChecked(state)
        else:
            self.state_label.setText("状态未知")
            self.quick_button.setChecked(False)

        self.quick_button.setVisible(self.has_quick_switch)
        self._update_button_text()
        self.style().unpolish(self.online_label)
        self.style().polish(self.online_label)

    def set_pending(self, pending: bool, desired_state: bool | None = None) -> None:
        self._pending = pending
        self.quick_button.setEnabled(not pending)
        if desired_state is not None:
            self.quick_button.setChecked(desired_state)
            self.state_label.setText("处理中…")
        elif not pending:
            self.update_device(self.device)
        self._update_button_text()

    def _request_quick_switch(self, checked: bool) -> None:
        if not self._pending:
            self.quick_switch_requested.emit(self.device.did, checked)

    def _update_button_text(self) -> None:
        if self._pending:
            self.quick_button.setText("处理中…")
        else:
            self.quick_button.setText("关闭" if self.quick_button.isChecked() else "开启")

