"""Generic MIoT Action button."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from app.models.action import DeviceAction


class ActionWidget(QFrame):
    action_requested = Signal(str)

    def __init__(self, action: DeviceAction, parent=None) -> None:
        super().__init__(parent)
        self.action = action
        self.setObjectName("actionRow")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 11, 14, 11)
        labels = QVBoxLayout()
        name = QLabel(action.description or action.name)
        name.setObjectName("propertyName")
        identifier = QLabel(action.name)
        identifier.setObjectName("propertyIdentifier")
        labels.addWidget(name)
        labels.addWidget(identifier)
        layout.addLayout(labels, 1)
        self.button = QPushButton("执行")
        self.button.setObjectName("actionButton")
        if action.parameters:
            self.button.setEnabled(False)
            self.button.setText("需要参数")
            self.button.setToolTip("参数化 Action 将在后续版本提供输入界面")
        self.button.clicked.connect(lambda: self.action_requested.emit(action.name))
        layout.addWidget(self.button)

    def set_pending(self, pending: bool) -> None:
        self.button.setEnabled(not pending and not self.action.parameters)
        self.button.setText("执行中…" if pending else ("需要参数" if self.action.parameters else "执行"))

