"""Application shell and background-operation coordinator."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QSize, QThreadPool, QTimer
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
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
from app.core.state_manager import StateManager
from app.services.tray_service import TrayService
from app.ui.pages.device_detail_page import DeviceDetailPage
from app.ui.pages.devices_page import DevicesPage
from app.ui.pages.favorites_page import FavoritesPage
from app.ui.style import load_stylesheet
from app.workers.base_worker import Worker


class MainWindow(QMainWindow):
    """Main navigation shell; all network work is delegated to Worker."""

    def __init__(
        self,
        device_manager: DeviceManager | None = None,
        *,
        state_manager: StateManager | None = None,
        auto_refresh: bool = True,
        enable_tray: bool = False,
    ) -> None:
        super().__init__()
        self.device_manager = device_manager
        self.state_manager = state_manager or (
            StateManager(device_manager) if device_manager is not None else None
        )
        self.thread_pool = QThreadPool(self)
        self.thread_pool.setMaxThreadCount(1)
        self._active_workers: set[Worker] = set()
        self._devices_loaded = False
        self._state_refresh_in_progress = False
        self._allow_exit = False
        self._return_page: QWidget | None = None
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(30_000)
        self.refresh_timer.timeout.connect(self.refresh_primary_states)

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
        self.favorites_button = QPushButton("★  收藏")
        self.favorites_button.setObjectName("navButton")
        self.favorites_button.setCheckable(True)
        sidebar_layout.addWidget(self.favorites_button)
        sidebar_layout.addStretch(1)
        version = QLabel("V0.1 Alpha")
        version.setObjectName("brandSubtitle")
        sidebar_layout.addWidget(version)
        root.addWidget(sidebar)

        self.pages = QStackedWidget()
        self.pages.setObjectName("pageStack")
        self.devices_page = DevicesPage()
        self.favorites_page = FavoritesPage()
        self.device_detail_page = DeviceDetailPage()
        self.pages.addWidget(self.devices_page)
        self.pages.addWidget(self.favorites_page)
        self.pages.addWidget(self.device_detail_page)
        root.addWidget(self.pages, 1)

        self.devices_button.clicked.connect(self.show_devices_page)
        self.favorites_button.clicked.connect(self.show_favorites_page)
        self.devices_page.refresh_requested.connect(self.manual_refresh)
        self.favorites_page.refresh_requested.connect(self.manual_refresh)
        self.devices_page.quick_switch_requested.connect(self.quick_switch)
        self.favorites_page.quick_switch_requested.connect(self.quick_switch)
        self.devices_page.detail_requested.connect(self.open_device_detail)
        self.favorites_page.detail_requested.connect(self.open_device_detail)
        self.devices_page.favorite_requested.connect(self.change_favorite)
        self.favorites_page.favorite_requested.connect(self.change_favorite)
        self.device_detail_page.back_requested.connect(self.show_return_page)
        self.device_detail_page.property_change_requested.connect(self.change_property)
        self.device_detail_page.action_requested.connect(self.run_device_action)

        self.tray_service = TrayService(self) if enable_tray else None
        if self.tray_service is not None:
            QApplication.instance().setQuitOnLastWindowClosed(False)
            self.tray_service.open_requested.connect(self.restore_from_tray)
            self.tray_service.refresh_requested.connect(self.manual_refresh)
            self.tray_service.quick_switch_requested.connect(self.quick_switch)
            self.tray_service.quit_requested.connect(self.quit_application)

        if self.device_manager is None:
            self.devices_page.status_label.setText("尚未连接设备服务")
        elif auto_refresh:
            self.refresh_devices()

    def refresh_devices(self) -> None:
        if self.device_manager is None:
            self.devices_page.show_error("设备服务不可用")
            return
        self.devices_page.set_loading(True)
        loader = getattr(
            self.device_manager,
            "sync_devices_fast",
            self.device_manager.sync_devices,
        )
        self._run_background(
            loader,
            on_result=self._on_devices_discovered,
            on_error=self._on_device_sync_error,
        )

    def _on_devices_discovered(self, devices) -> None:
        self._show_device_snapshot(devices)
        if getattr(self.device_manager, "needs_enrichment", False):
            self.devices_page.status_label.setText(
                f"已显示 {len(devices)} 台设备 · 正在后台加载控制能力…"
            )
            self._run_background(
                self.device_manager.enrich_devices,
                on_result=self._on_devices_synced,
                on_error=self._on_enrichment_error,
                on_finished=lambda: self.devices_page.set_loading(False),
            )
            return
        self._on_devices_synced(devices)
        self.devices_page.set_loading(False)

    def _show_device_snapshot(self, devices) -> None:
        self._devices_loaded = True
        self.devices_page.set_devices(devices)
        self.favorites_page.set_devices(devices)
        self._update_tray(devices)

    def _on_devices_synced(self, devices) -> None:
        self._show_device_snapshot(devices)
        if self.state_manager is not None:
            self.state_manager.seed(devices)
            self.refresh_timer.start()

    def _on_device_sync_error(self, error: Exception) -> None:
        self.devices_page.show_error(str(error))
        self.devices_page.set_loading(False)

    def _on_enrichment_error(self, error: Exception) -> None:
        self.devices_page.status_label.setText(f"设备已显示 · 控制能力加载失败：{error}")

    def manual_refresh(self) -> None:
        if self._devices_loaded and self.state_manager is not None:
            self.refresh_primary_states()
        else:
            self.refresh_devices()

    def refresh_primary_states(self) -> None:
        self.refresh_states(capability_names={"on"})

    def refresh_states(
        self,
        dids: set[str] | None = None,
        capability_names: set[str] | None = None,
    ) -> None:
        if self.state_manager is None or self._state_refresh_in_progress:
            return
        self._state_refresh_in_progress = True
        self.devices_page.set_state_loading(True)
        self.favorites_page.set_state_loading(True)

        def complete(_snapshot: Any) -> None:
            if self.device_manager is None:
                return
            devices = self.device_manager.devices
            self.devices_page.update_states(devices)
            self.favorites_page.update_states(
                tuple(device for device in devices if device.favorite)
            )
            self._update_tray(devices)
            if self.device_detail_page.device is not None:
                active = self.device_manager.get_device(self.device_detail_page.device.did)
                self.device_detail_page.update_state(active)

        def fail(error: Exception) -> None:
            self.devices_page.show_refresh_error(str(error))
            self.favorites_page.show_refresh_error(str(error))

        def finished() -> None:
            self._state_refresh_in_progress = False
            self.devices_page.set_state_loading(False)
            self.favorites_page.set_state_loading(False)

        self._run_background(
            self.state_manager.refresh,
            dids,
            capability_names,
            on_result=complete,
            on_error=fail,
            on_finished=finished,
        )

    def quick_switch(self, did: str, desired_state: bool) -> None:
        if self.device_manager is None:
            return
        self.devices_page.begin_quick_switch(did, desired_state)
        self.favorites_page.begin_quick_switch(did, desired_state)

        def complete(_result: Any) -> None:
            self.devices_page.finish_quick_switch(did, success=True)
            self.favorites_page.finish_quick_switch(did, success=True)
            self._update_tray(self.device_manager.devices)
            self.refresh_states({did}, {"on"})

        def fail(error: Exception) -> None:
            self.devices_page.finish_quick_switch(did, success=False, error_message=str(error))
            self.favorites_page.finish_quick_switch(
                did, success=False, error_message=str(error)
            )
            self._update_tray(self.device_manager.devices)

        self._run_background(
            self.device_manager.set_property,
            did,
            "on",
            desired_state,
            on_result=complete,
            on_error=fail,
        )

    def show_devices_page(self) -> None:
        self.pages.setCurrentWidget(self.devices_page)
        self.devices_button.setChecked(True)
        self.favorites_button.setChecked(False)

    def show_favorites_page(self) -> None:
        self.pages.setCurrentWidget(self.favorites_page)
        self.devices_button.setChecked(False)
        self.favorites_button.setChecked(True)

    def show_return_page(self) -> None:
        if self._return_page is self.favorites_page:
            self.show_favorites_page()
        else:
            self.show_devices_page()

    def open_device_detail(self, did: str) -> None:
        if self.device_manager is None:
            return
        try:
            device = self.device_manager.get_device(did)
        except Exception as error:
            self.devices_page.show_error(str(error))
            return
        self._return_page = self.pages.currentWidget()
        self.device_detail_page.set_device(device)
        self.pages.setCurrentWidget(self.device_detail_page)
        self.devices_button.setChecked(False)
        self.favorites_button.setChecked(False)
        self.refresh_states({did})

    def change_favorite(self, did: str, favorite: bool) -> None:
        if self.device_manager is None:
            return
        try:
            self.device_manager.set_favorite(did, favorite)
        except Exception as error:
            self.devices_page.show_error(str(error))
            return
        devices = self.device_manager.devices
        self.devices_page.set_devices(devices)
        self.favorites_page.set_devices(devices)
        self._update_tray(devices)

    def change_property(self, did: str, name: str, value: Any) -> None:
        if self.device_manager is None:
            return
        self.device_detail_page.begin_property_update(name)

        def complete(_result: Any) -> None:
            self.device_detail_page.finish_property_update(name, True, value=value)
            card = self.devices_page.cards.get(did)
            if card is not None:
                card.update_device(card.device)
            self.refresh_states({did}, {name})

        def fail(error: Exception) -> None:
            self.device_detail_page.finish_property_update(name, False, str(error))

        self._run_background(
            self.device_manager.set_property,
            did,
            name,
            value,
            on_result=complete,
            on_error=fail,
        )

    def run_device_action(self, did: str, name: str) -> None:
        if self.device_manager is None:
            return
        self.device_detail_page.begin_action(name)

        def complete(_result: Any) -> None:
            self.device_detail_page.finish_action(name, True)
            self.refresh_states({did})

        def fail(error: Exception) -> None:
            self.device_detail_page.finish_action(name, False, str(error))

        self._run_background(
            self.device_manager.run_action,
            did,
            name,
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

    def _update_tray(self, devices) -> None:
        if self.tray_service is not None:
            self.tray_service.update_devices(tuple(devices))

    def restore_from_tray(self) -> None:
        self.show()
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def quit_application(self) -> None:
        self._allow_exit = True
        self.refresh_timer.stop()
        QApplication.instance().quit()

    def closeEvent(self, event: QCloseEvent) -> None:
        if (
            not self._allow_exit
            and self.tray_service is not None
            and self.tray_service.available
        ):
            event.ignore()
            self.hide()
            self.tray_service.show_hidden_message()
            return
        super().closeEvent(event)
