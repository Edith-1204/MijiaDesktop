"""Capability-driven device detail page."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.models.device import BaseDevice
from app.ui.device_controls.generic_control import GenericDeviceControl


class DeviceDetailPage(QWidget):
    back_requested = Signal()
    property_change_requested = Signal(str, str, object)
    action_requested = Signal(str, str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.device: BaseDevice | None = None
        self.generic_control: GenericDeviceControl | None = None
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        header = QHBoxLayout()
        self.back_button = QPushButton("← 返回")
        self.back_button.setObjectName("backButton")
        self.back_button.clicked.connect(self.back_requested)
        header.addWidget(self.back_button)
        header.addStretch(1)
        root.addLayout(header)
        self.name_label = QLabel("设备详情")
        self.name_label.setObjectName("pageTitle")
        self.summary_label = QLabel()
        self.summary_label.setObjectName("pageStatus")
        root.addWidget(self.name_label)
        root.addWidget(self.summary_label)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("detailTabs")
        self.control_scroll = QScrollArea()
        self.control_scroll.setWidgetResizable(True)
        self.control_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.tabs.addTab(self.control_scroll, "通用控制")
        self.info_widget = QWidget()
        self.info_form = QFormLayout(self.info_widget)
        self.tabs.addTab(self.info_widget, "设备信息")
        root.addWidget(self.tabs, 1)

    def set_device(self, device: BaseDevice) -> None:
        self.device = device
        self.name_label.setText(device.name)
        self.summary_label.setText(f"{device.device_type.value} · {'在线' if device.online else '离线/未知'}")
        if self.generic_control is not None:
            self.generic_control.deleteLater()
        self.generic_control = GenericDeviceControl(device)
        self.generic_control.property_change_requested.connect(
            lambda name, value: self.property_change_requested.emit(device.did, name, value)
        )
        self.generic_control.action_requested.connect(
            lambda name: self.action_requested.emit(device.did, name)
        )
        self.control_scroll.setWidget(self.generic_control)
        while self.info_form.rowCount():
            self.info_form.removeRow(0)
        self.info_form.addRow("名称", QLabel(device.name))
        self.info_form.addRow("Model", QLabel(device.model or "—"))
        self.info_form.addRow("DID", QLabel(device.did))
        self.info_form.addRow("类型", QLabel(device.device_type.value))
        self.info_form.addRow("状态", QLabel("在线" if device.online else "离线/未知"))

    def begin_property_update(self, name: str) -> None:
        if self.generic_control is not None:
            self.generic_control.begin_property_update(name)
        self.summary_label.setText(f"正在设置 {name}…")

    def finish_property_update(self, name: str, success: bool, message: str = "") -> None:
        if self.generic_control is not None:
            self.generic_control.finish_property_update(name, success)
        self.summary_label.setText("设置成功" if success else f"设置失败：{message}")

    def begin_action(self, name: str) -> None:
        if self.generic_control is not None:
            self.generic_control.set_action_pending(name, True)
        self.summary_label.setText(f"正在执行 {name}…")

    def finish_action(self, name: str, success: bool, message: str = "") -> None:
        if self.generic_control is not None:
            self.generic_control.set_action_pending(name, False)
        self.summary_label.setText("Action 执行成功" if success else f"Action 失败：{message}")

