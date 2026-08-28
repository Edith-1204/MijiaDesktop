"""The Phase 3 application shell and background-operation coordinator."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QSize, QThreadPool
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.core.device_manager import DeviceManager
from app.ui.pages.devices_page import DevicesPage
from app.ui.style import load_stylesheet
from app.workers.base_worker import Worker


class MainWindow(QMainWindow):
    """Main navigation shell; all network work is delegated to Worker."""

    def __init__(
        self,
        device_manager: DeviceManager | None = None,
        *,
        auto_refresh: bool = True,
    ) -> None:
        super().__init__()
        self.device_manager = device_manager
        self.thread_pool = QThreadPool(self)
        self.thread_pool.setMaxThreadCount(1)
        self._active_workers: set[Worker] = set()

        self.setWindowTitle("Mijia Desktop")
        self.resize(QSize(1080, 720))
        self.setMinimumSize(QSize(760, 520))
        self.setStyleSheet(load_stylesheet())

        root_widget = QWidget()
        root_widget.setObjectName("windowRoot")
        root = QHBoxLayout(root_widget)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.setCentralWidget(root_widget)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(190)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(18, 22, 18, 22)
        sidebar_layout.setSpacing(8)
        brand = QLabel("Mijia Desktop")
        brand.setObjectName("brandTitle")
        subtitle = QLabel("米家桌面控制中心")
        subtitle.setObjectName("brandSubtitle")
        sidebar_layout.addWidget(brand)
        sidebar_layout.addWidget(subtitle)
        sidebar_layout.addSpacing(22)
        self.devices_button = QPushButton("▦  全部设备")
        self.devices_button.setObjectName("navButton")
        self.devices_button.setCheckable(True)
        self.devices_button.setChecked(True)
        sidebar_layout.addWidget(self.devices_button)
        sidebar_layout.addStretch(1)
        version = QLabel("V0.1 Alpha")
        version.setObjectName("brandSubtitle")
        sidebar_layout.addWidget(version)
        root.addWidget(sidebar)

        self.pages = QStackedWidget()
        self.devices_page = DevicesPage()
        self.pages.addWidget(self.devices_page)
        root.addWidget(self.pages, 1)

        self.devices_button.clicked.connect(lambda: self.pages.setCurrentWidget(self.devices_page))
        self.devices_page.refresh_requested.connect(self.refresh_devices)
        self.devices_page.quick_switch_requested.connect(self.quick_switch)

        if self.device_manager is None:
            self.devices_page.status_label.setText("尚未连接设备服务")
        elif auto_refresh:
            self.refresh_devices()

    def refresh_devices(self) -> None:
        if self.device_manager is None:
            self.devices_page.show_error("设备服务不可用")
            return
        self.devices_page.set_loading(True)
        self._run_background(
            self.device_manager.sync_devices,
            on_result=self.devices_page.set_devices,
            on_error=lambda error: self.devices_page.show_error(str(error)),
            on_finished=lambda: self.devices_page.set_loading(False),
        )

    def quick_switch(self, did: str, desired_state: bool) -> None:
        if self.device_manager is None:
            return
        self.devices_page.begin_quick_switch(did, desired_state)

        def complete(_result: Any) -> None:
            self.devices_page.finish_quick_switch(did, success=True)

        def fail(error: Exception) -> None:
            self.devices_page.finish_quick_switch(did, success=False, error_message=str(error))

        self._run_background(
            self.device_manager.set_property,
            did,
            "on",
            desired_state,
            on_result=complete,
            on_error=fail,
        )

    def _run_background(
        self,
        function: Callable[..., Any],
        *args: Any,
        on_result: Callable[[Any], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
        on_finished: Callable[[], None] | None = None,
    ) -> None:
        worker = Worker(function, *args)
        self._active_workers.add(worker)
        if on_result is not None:
            worker.signals.result.connect(on_result)
        if on_error is not None:
            worker.signals.error.connect(on_error)
        if on_finished is not None:
            worker.signals.finished.connect(on_finished)
        worker.signals.finished.connect(lambda: self._active_workers.discard(worker))
        self.thread_pool.start(worker)
