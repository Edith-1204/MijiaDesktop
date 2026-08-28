"""Focused controls for lights."""

from __future__ import annotations

from typing import Any

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QColorDialog, QPushButton

from app.models.capability import DeviceCapability
from app.ui.device_controls.specialized_control import SpecializedDeviceControl
from app.ui.widgets.property_widget import BasePropertyWidget


class ColorPropertyWidget(BasePropertyWidget):
    """Present MIoT's packed RGB integer as an actual color picker."""

    def __init__(self, capability: DeviceCapability, parent=None) -> None:
        super().__init__(capability, parent)
        self._value = 0
        self.editor = QPushButton()
        self.editor.setObjectName("colorEditor")
        self.editor.clicked.connect(self._choose_color)
        self.editor_layout.addWidget(self.editor)
        self._set_editor_value(capability.value or 0)

    def _choose_color(self) -> None:
        selected = QColorDialog.getColor(
            QColor.fromRgb(self._value),
            self,
            "选择灯光颜色",
        )
        if selected.isValid():
            self._set_editor_value(selected.rgb() & 0xFFFFFF)
            self.request_change(self._value)

    def _editor_value(self) -> int:
        return self._value

    def _set_editor_value(self, value: Any) -> None:
        self._value = int(value or 0) & 0xFFFFFF
        color = QColor.fromRgb(self._value)
        foreground = "#111111" if color.lightness() > 150 else "#ffffff"
        self.editor.setText(color.name().upper())
        self.editor.setStyleSheet(
            f"background: {color.name()}; color: {foreground}; "
            "border: 1px solid #aeb5bd; border-radius: 7px; padding: 8px 15px;"
        )


class LightControl(SpecializedDeviceControl):
    title = "灯光控制"
    description = "快速调整电源、亮度、色温、颜色和模式。"
    capability_names = ("on", "brightness", "color-temperature", "color", "mode")

    def create_capability_widget(self, capability: DeviceCapability) -> BasePropertyWidget:
        if capability.name == "color" and capability.writable:
            return ColorPropertyWidget(capability)
        return super().create_capability_widget(capability)
