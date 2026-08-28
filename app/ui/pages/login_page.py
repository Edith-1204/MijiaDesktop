"""In-application Xiaomi QR login page."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget


class LoginPage(QWidget):
    login_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("loginPage")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title = QLabel("登录米家")
        title.setObjectName("pageTitle")
        self.qr_label = QLabel("点击下方按钮生成二维码")
        self.qr_label.setObjectName("qrCode")
        self.qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qr_label.setMinimumSize(260, 260)
        self.status_label = QLabel("使用米家 APP 扫码登录")
        self.status_label.setObjectName("pageStatus")
        self.login_button = QPushButton("生成登录二维码")
        self.login_button.setObjectName("actionButton")
        self.login_button.clicked.connect(self.login_requested)
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.qr_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.login_button, alignment=Qt.AlignmentFlag.AlignCenter)

    def set_loading(self, loading: bool) -> None:
        self.login_button.setEnabled(not loading)
        self.login_button.setText("正在登录…" if loading else "重新生成二维码")

    def show_qr(self, path: Path) -> None:
        pixmap = QPixmap(str(path))
        self.qr_label.setPixmap(
            pixmap.scaled(
                260,
                260,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        self.status_label.setText("请使用米家 APP 扫码确认")

    def show_error(self, message: str) -> None:
        self.status_label.setText(f"登录失败：{message}")
        self.set_loading(False)
