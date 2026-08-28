"""Application settings page."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.settings_manager import REFRESH_INTERVALS, SettingsManager, ThemeMode


class SettingsPage(QWidget):
    theme_changed = Signal(str)
    refresh_interval_changed = Signal(int)
    startup_changed = Signal(bool)
    advanced_mode_changed = Signal(bool)
    relogin_requested = Signal()
    logout_requested = Signal()

    def __init__(self, settings: SettingsManager, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.setObjectName("settingsPage")
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)
        title = QLabel("设置")
        title.setObjectName("pageTitle")
        self.status_label = QLabel("设置会自动保存")
        self.status_label.setObjectName("pageStatus")
        root.addWidget(title)
        root.addWidget(self.status_label)

        panel = QFrame()
        panel.setObjectName("settingsPanel")
        form = QFormLayout(panel)
        form.setContentsMargins(18, 18, 18, 18)
        form.setSpacing(14)

        self.theme_combo = QComboBox()
        self.theme_combo.addItem("跟随 Windows", ThemeMode.SYSTEM.value)
        self.theme_combo.addItem("浅色", ThemeMode.LIGHT.value)
        self.theme_combo.addItem("深色", ThemeMode.DARK.value)
        self.theme_combo.setCurrentIndex(self.theme_combo.findData(settings.theme.value))
        self.theme_combo.currentIndexChanged.connect(
            lambda: self.theme_changed.emit(self.theme_combo.currentData())
        )
        form.addRow("主题", self.theme_combo)

        self.refresh_combo = QComboBox()
        for seconds in REFRESH_INTERVALS:
            self.refresh_combo.addItem("手动" if seconds == 0 else f"{seconds} 秒", seconds)
        self.refresh_combo.setCurrentIndex(
            self.refresh_combo.findData(settings.refresh_interval)
        )
        self.refresh_combo.currentIndexChanged.connect(
            lambda: self.refresh_interval_changed.emit(self.refresh_combo.currentData())
        )
        form.addRow("状态刷新周期", self.refresh_combo)

        self.startup_checkbox = QCheckBox("开机自动运行")
        self.startup_checkbox.setChecked(settings.startup_enabled)
        self.startup_checkbox.toggled.connect(
            lambda enabled: self.startup_changed.emit(enabled)
        )
        form.addRow("系统", self.startup_checkbox)

        self.advanced_checkbox = QCheckBox("显示 MIoT 调试信息")
        self.advanced_checkbox.setChecked(settings.advanced_mode)
        self.advanced_checkbox.toggled.connect(
            lambda enabled: self.advanced_mode_changed.emit(enabled)
        )
        form.addRow("高级模式", self.advanced_checkbox)
        root.addWidget(panel)

        account = QFrame()
        account.setObjectName("settingsPanel")
        account_layout = QHBoxLayout(account)
        account_layout.addWidget(QLabel("米家账号"))
        account_layout.addStretch(1)
        self.relogin_button = QPushButton("重新登录")
        self.logout_button = QPushButton("退出账号")
        self.relogin_button.clicked.connect(self.relogin_requested)
        self.logout_button.clicked.connect(self.logout_requested)
        account_layout.addWidget(self.relogin_button)
        account_layout.addWidget(self.logout_button)
        root.addWidget(account)
        root.addStretch(1)

    def show_status(self, message: str) -> None:
        self.status_label.setText(message)
