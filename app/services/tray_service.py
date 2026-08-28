"""Windows system-tray integration."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QStyle, QSystemTrayIcon, QWidget

from app.models.device import BaseDevice


class TrayService(QObject):
    open_requested = Signal()
    refresh_requested = Signal()
    quick_switch_requested = Signal(str, bool)
    quit_requested = Signal()

    def __init__(self, window: QWidget) -> None:
        super().__init__(window)
        self.window = window
        self.available = QSystemTrayIcon.isSystemTrayAvailable()
        icon = window.windowIcon()
        if icon.isNull():
            icon = window.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        self.icon: QIcon = icon
        self.tray = QSystemTrayIcon(self.icon, window)
        self.tray.setToolTip("Mijia Desktop")
        self.menu = QMenu(window)
        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(self._on_activated)
        self.update_devices(())
        if self.available:
            self.tray.show()

    def update_devices(self, devices: tuple[BaseDevice, ...]) -> None:
        self.menu.clear()
        title = self.menu.addAction("Mijia Desktop")
        title.setEnabled(False)
        self.menu.addSeparator()

        favorites = [
            device
            for device in devices
            if device.favorite
            and (capability := device.capability("on")) is not None
            and capability.writable
        ]
        if favorites:
            for device in favorites:
                action = QAction(f"★ {device.name}", self.menu)
                action.setCheckable(True)
                action.setChecked(bool(device.primary_state))
                action.triggered.connect(
                    lambda checked, did=device.did: self.quick_switch_requested.emit(
                        did, checked
                    )
                )
                self.menu.addAction(action)
        else:
            empty = self.menu.addAction("暂无可快速控制的收藏设备")
            empty.setEnabled(False)

        self.menu.addSeparator()
        open_action = self.menu.addAction("打开主界面")
        open_action.triggered.connect(self.open_requested)
        refresh_action = self.menu.addAction("刷新设备")
        refresh_action.triggered.connect(self.refresh_requested)
        self.menu.addSeparator()
        quit_action = self.menu.addAction("退出")
        quit_action.triggered.connect(self.quit_requested)

    def show_hidden_message(self) -> None:
        if self.available:
            self.tray.showMessage(
                "Mijia Desktop",
                "应用仍在后台运行，可从通知区域重新打开。",
                self.icon,
                2500,
            )

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in {
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        }:
            self.open_requested.emit()
