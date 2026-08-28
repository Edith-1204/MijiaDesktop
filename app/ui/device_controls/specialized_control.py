"""Capability-driven base class for focused device controls."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from app.models.capability import DeviceCapability
from app.models.device import BaseDevice
from app.ui.widgets.property_widget import BasePropertyWidget, create_property_widget


class SpecializedDeviceControl(QWidget):
    """Show a small, ordered subset of capabilities for frequent operations."""

    property_change_requested = Signal(str, object)

    title = "常用控制"
    description = "根据设备能力自动显示可用控件"
    capability_names: tuple[str, ...] = ()

    def __init__(self, device: BaseDevice, parent=None) -> None:
        super().__init__(parent)
        self.device = device
        self.property_widgets: dict[str, BasePropertyWidget] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        title = QLabel(self.title)
        title.setObjectName("controlTitle")
        description = QLabel(self.description)
        description.setObjectName("controlDescription")
        description.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(description)

        seen: set[str] = set()
        for requested_name in self.capability_names:
            capability = device.capability(requested_name)
            if capability is None or capability.name in seen:
                continue
            seen.add(capability.name)
            widget = self.create_capability_widget(capability)
            widget.change_requested.connect(self.property_change_requested)
            self.property_widgets[capability.name] = widget
            layout.addWidget(widget)

        if not self.property_widgets:
            empty = QLabel("该设备没有可用的常用控制")
            empty.setObjectName("emptyInline")
            layout.addWidget(empty)
        layout.addStretch(1)

    def create_capability_widget(self, capability: DeviceCapability) -> BasePropertyWidget:
        return create_property_widget(capability)

    def begin_property_update(self, name: str) -> None:
        widget = self.property_widgets.get(name)
        if widget is not None:
            widget.set_pending(True)

    def finish_property_update(self, name: str, success: bool, value=None) -> None:
        widget = self.property_widgets.get(name)
        if widget is not None:
            widget.finish(success, value)
