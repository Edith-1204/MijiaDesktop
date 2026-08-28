"""Capability-driven device detail page."""

from __future__ import annotations

import json

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.models.device import BaseDevice
from app.ui.device_controls.factory import create_specialized_control
from app.ui.device_controls.generic_control import GenericDeviceControl
from app.ui.device_controls.specialized_control import SpecializedDeviceControl


class DeviceDetailPage(QWidget):
    back_requested = Signal()
    property_change_requested = Signal(str, str, object)
    action_requested = Signal(str, str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("deviceDetailPage")
        self.device: BaseDevice | None = None
        self.generic_control: GenericDeviceControl | None = None
        self.action_control: GenericDeviceControl | None = None
        self.specialized_control: SpecializedDeviceControl | None = None
        self.advanced_mode = False
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
        self.common_scroll = QScrollArea()
        self.common_scroll.setObjectName("detailScroll")
        self.common_scroll.viewport().setObjectName("detailViewport")
        self.common_scroll.setWidgetResizable(True)
        self.common_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.tabs.addTab(self.common_scroll, "常用控制")
        self.control_scroll = QScrollArea()
        self.control_scroll.setObjectName("detailScroll")
        self.control_scroll.viewport().setObjectName("detailViewport")
        self.control_scroll.setWidgetResizable(True)
        self.control_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.tabs.addTab(self.control_scroll, "全部属性")
        self.action_scroll = QScrollArea()
        self.action_scroll.setObjectName("detailScroll")
        self.action_scroll.viewport().setObjectName("detailViewport")
        self.action_scroll.setWidgetResizable(True)
        self.action_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.tabs.addTab(self.action_scroll, "Actions")
        self.info_widget = QWidget()
        self.info_widget.setObjectName("deviceInfo")
        self.info_form = QFormLayout(self.info_widget)
        self.tabs.addTab(self.info_widget, "设备信息")
        self.debug_output = QPlainTextEdit()
        self.debug_output.setObjectName("debugOutput")
        self.debug_output.setReadOnly(True)
        self.debug_tab_index = self.tabs.addTab(self.debug_output, "MIoT Debug")
        self.tabs.setTabVisible(self.debug_tab_index, False)
        root.addWidget(self.tabs, 1)

    def set_device(self, device: BaseDevice) -> None:
        self.device = device
        self.name_label.setText(device.name)
        status = "在线" if device.online else "离线/未知"
        self.summary_label.setText(f"{device.device_type.value} · {status}")

        self.specialized_control = create_specialized_control(device)
        self.tabs.setTabVisible(0, self.specialized_control is not None)
        if self.specialized_control is not None:
            self.specialized_control.property_change_requested.connect(
                lambda name, value: self.property_change_requested.emit(device.did, name, value)
            )
            self._replace_scroll_widget(self.common_scroll, self.specialized_control)
        else:
            self._clear_scroll_widget(self.common_scroll)

        self.generic_control = GenericDeviceControl(device, include_actions=False)
        self.generic_control.property_change_requested.connect(
            lambda name, value: self.property_change_requested.emit(device.did, name, value)
        )
        self._replace_scroll_widget(self.control_scroll, self.generic_control)

        self.action_control = GenericDeviceControl(device, include_properties=False)
        self.action_control.action_requested.connect(
            lambda name: self.action_requested.emit(device.did, name)
        )
        self._replace_scroll_widget(self.action_scroll, self.action_control)
        self.tabs.setCurrentIndex(0 if self.specialized_control is not None else 1)

        while self.info_form.rowCount():
            self.info_form.removeRow(0)
        self.info_form.addRow("名称", QLabel(device.name))
        self.info_form.addRow("类型", QLabel(device.device_type.value))
        self.info_form.addRow("状态", QLabel("在线" if device.online else "离线/未知"))
        self._refresh_debug_output()

    def set_advanced_mode(self, enabled: bool) -> None:
        self.advanced_mode = enabled
        self.tabs.setTabVisible(self.debug_tab_index, enabled)
        self._refresh_debug_output()

    def _refresh_debug_output(self) -> None:
        if self.device is None:
            self.debug_output.clear()
            return
        device = self.device
        payload = {
            "name": device.name,
            "model": device.model,
            "did": device.did,
            "type": device.device_type.value,
            "online": device.online,
            "properties": [
                {
                    "name": capability.name,
                    "description": capability.description,
                    "siid": capability.siid,
                    "piid": capability.piid,
                    "value": capability.value,
                    "value_type": capability.value_type,
                    "readable": capability.readable,
                    "writable": capability.writable,
                    "unit": capability.unit,
                    "range": [capability.min_value, capability.max_value, capability.step],
                    "enum_values": capability.enum_values,
                    "metadata": capability.metadata,
                }
                for capability in device.properties.values()
            ],
            "actions": [
                {
                    "name": action.name,
                    "description": action.description,
                    "siid": action.siid,
                    "aiid": action.aiid,
                    "parameters": action.parameters,
                    "metadata": action.metadata,
                }
                for action in device.actions.values()
            ],
            "metadata": device.metadata,
        }
        self.debug_output.setPlainText(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str)
        )

    def begin_property_update(self, name: str) -> None:
        if self.specialized_control is not None:
            self.specialized_control.begin_property_update(name)
        if self.generic_control is not None:
            self.generic_control.begin_property_update(name)
        self.summary_label.setText(f"正在设置 {name}…")

    def update_state(self, device: BaseDevice) -> None:
        """Apply refreshed values without rebuilding the current detail page."""
        if self.device is None or self.device.did != device.did:
            return
        self.device = device
        status = "在线" if device.online else "离线/未知"
        self.summary_label.setText(f"{device.device_type.value} · {status} · 状态已刷新")
        for control in (self.specialized_control, self.generic_control):
            if control is None:
                continue
            for name, widget in control.property_widgets.items():
                capability = device.capability(name)
                if capability is not None:
                    widget.finish(True, capability.value)
        self._refresh_debug_output()

    def finish_property_update(
        self,
        name: str,
        success: bool,
        message: str = "",
        value=None,
    ) -> None:
        if self.specialized_control is not None:
            self.specialized_control.finish_property_update(name, success, value)
        if self.generic_control is not None:
            self.generic_control.finish_property_update(name, success, value)
        self.summary_label.setText("设置成功" if success else f"设置失败：{message}")

    def begin_action(self, name: str) -> None:
        if self.action_control is not None:
            self.action_control.set_action_pending(name, True)
        self.summary_label.setText(f"正在执行 {name}…")

    def finish_action(self, name: str, success: bool, message: str = "") -> None:
        if self.action_control is not None:
            self.action_control.set_action_pending(name, False)
        self.summary_label.setText("Action 执行成功" if success else f"Action 失败：{message}")

    @staticmethod
    def _replace_scroll_widget(scroll: QScrollArea, widget: QWidget) -> None:
        DeviceDetailPage._clear_scroll_widget(scroll)
        widget.setObjectName("detailContent")
        scroll.setWidget(widget)

    @staticmethod
    def _clear_scroll_widget(scroll: QScrollArea) -> None:
        previous = scroll.takeWidget()
        if previous is not None:
            previous.deleteLater()
