"""Build a usable device UI entirely from capabilities and actions."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from app.models.device import BaseDevice
from app.ui.widgets.action_widget import ActionWidget
from app.ui.widgets.property_widget import BasePropertyWidget, create_property_widget


class GenericDeviceControl(QWidget):
    property_change_requested = Signal(str, object)
    action_requested = Signal(str)

    def __init__(
        self,
        device: BaseDevice,
        parent=None,
        *,
        include_properties: bool = True,
        include_actions: bool = True,
    ) -> None:
        super().__init__(parent)
        self.device = device
        self.property_widgets: dict[str, BasePropertyWidget] = {}
        self.action_widgets: dict[str, ActionWidget] = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        if include_properties:
            property_title = QLabel("全部属性")
            property_title.setObjectName("sectionTitle")
            layout.addWidget(property_title)
            for capability in device.properties.values():
                widget = create_property_widget(capability)
                widget.change_requested.connect(self.property_change_requested)
                self.property_widgets[capability.name] = widget
                layout.addWidget(widget)
            if not device.properties:
                layout.addWidget(self._empty_label("该设备没有可用的 MIoT Property"))

        if include_actions:
            action_title = QLabel("Actions")
            action_title.setObjectName("sectionTitle")
            layout.addWidget(action_title)
            for action in device.actions.values():
                widget = ActionWidget(action)
                widget.action_requested.connect(self.action_requested)
                self.action_widgets[action.name] = widget
                layout.addWidget(widget)
            if not device.actions:
                layout.addWidget(self._empty_label("该设备没有可用的 MIoT Action"))
        layout.addStretch(1)

    def begin_property_update(self, name: str) -> None:
        widget = self.property_widgets.get(name)
        if widget is not None:
            widget.set_pending(True)

    def finish_property_update(self, name: str, success: bool, value=None) -> None:
        widget = self.property_widgets.get(name)
        if widget is not None:
            widget.finish(success, value)

    def set_action_pending(self, name: str, pending: bool) -> None:
        widget = self.action_widgets.get(name)
        if widget is not None:
            widget.set_pending(pending)

    @staticmethod
    def _empty_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("emptyInline")
        return label
