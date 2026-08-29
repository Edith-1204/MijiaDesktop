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

from app import __version__
from app.application import load_application_icon
from app.core.account_manager import AccountManager
from app.core.device_manager import DeviceManager
from app.core.settings_manager import SettingsManager, ThemeMode
from app.core.state_manager import StateManager
from app.services.startup_service import StartupService
from app.services.theme_service import ThemeService
from app.services.tray_service import TrayService
from app.ui.pages.device_detail_page import DeviceDetailPage
from app.ui.pages.devices_page import DevicesPage
from app.ui.pages.favorites_page import FavoritesPage
from app.ui.pages.login_page import LoginPage
from app.ui.pages.settings_page import SettingsPage
from app.ui.style import load_stylesheet
from app.workers.base_worker import Worker


POST_OPERATION_REFRESH_DELAY_MS = 300


class MainWindow(QMainWindow):
    """Main navigation shell; all network work is delegated to Worker."""

    def __init__(
        self,
        device_manager: DeviceManager | None = None,
        *,
        state_manager: StateManager | None = None,
        settings_manager: SettingsManager | None = None,
        theme_service: ThemeService | None = None,
        startup_service: StartupService | None = None,
        account_manager: AccountManager | None = None,
        auto_refresh: bool = True,
        enable_tray: bool = False,
    ) -> None:
        super().__init__()
        self.device_manager = device_manager
        self.state_manager = state_manager or (
            StateManager(device_manager) if device_manager is not None else None
        )
        self.settings_manager = settings_manager or SettingsManager()
        self.theme_service = theme_service
        self.startup_service = startup_service
        self.account_manager = account_manager
        self.thread_pool = QThreadPool(self)
        self.thread_pool.setMaxThreadCount(1)
        self._active_workers: set[Worker] = set()
        self._devices_loaded = False
        self._state_refresh_in_progress = False
        self._pending_operation_refresh_dids: set[str] = set()
        self._login_attempt = 0
        self._login_in_progress = False
        self._allow_exit = False
        self._return_page: QWidget | None = None
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(self.settings_manager.refresh_interval * 1_000)
        self.refresh_timer.timeout.connect(self.refresh_primary_states)

        self.setWindowTitle("Mijia Desktop")
        self.setWindowIcon(load_application_icon())
        self.resize(QSize(1080, 720))
        self.setMinimumSize(QSize(760, 520))
        if self.theme_service is not None:
            self.theme_service.apply(self.settings_manager.theme)
        else:
            fallback_theme = (
                "dark" if self.settings_manager.theme is ThemeMode.DARK else "light"
            )
            self.setStyleSheet(load_stylesheet(fallback_theme))

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
        self.settings_button = QPushButton("⚙  设置")
        self.settings_button.setObjectName("navButton")
        self.settings_button.setCheckable(True)
        sidebar_layout.addWidget(self.settings_button)
        version = QLabel(f"V{__version__}")
        version.setObjectName("brandSubtitle")
        sidebar_layout.addWidget(version)
        root.addWidget(sidebar)

        self.pages = QStackedWidget()
        self.pages.setObjectName("pageStack")
        self.devices_page = DevicesPage()
        self.favorites_page = FavoritesPage()
        self.device_detail_page = DeviceDetailPage()
        self.settings_page = SettingsPage(self.settings_manager)
        self.login_page = LoginPage()
        self.pages.addWidget(self.devices_page)
        self.pages.addWidget(self.favorites_page)
        self.pages.addWidget(self.device_detail_page)
        self.pages.addWidget(self.settings_page)
        self.pages.addWidget(self.login_page)
        root.addWidget(self.pages, 1)

        self.device_detail_page.set_advanced_mode(self.settings_manager.advanced_mode)
        account_available = self.account_manager is not None
        self.settings_page.relogin_button.setEnabled(account_available)
        self.settings_page.logout_button.setEnabled(account_available)
        self.login_page.login_button.setEnabled(account_available)

        self.devices_button.clicked.connect(self.show_devices_page)
        self.favorites_button.clicked.connect(self.show_favorites_page)
        self.settings_button.clicked.connect(self.show_settings_page)
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
        self.settings_page.theme_changed.connect(self.change_theme)
        self.settings_page.refresh_interval_changed.connect(
            self.change_refresh_interval
        )
        self.settings_page.startup_changed.connect(self.change_startup)
        self.settings_page.advanced_mode_changed.connect(self.change_advanced_mode)
        self.settings_page.relogin_requested.connect(self.relogin)
        self.settings_page.logout_requested.connect(self.logout)
        self.login_page.login_requested.connect(self.begin_login)

        self.tray_service = TrayService(self) if enable_tray else None
        if self.tray_service is not None:
            QApplication.instance().setQuitOnLastWindowClosed(False)
            self.tray_service.open_requested.connect(self.restore_from_tray)
            self.tray_service.refresh_requested.connect(self.manual_refresh)
            self.tray_service.quick_switch_requested.connect(self.quick_switch)
            self.tray_service.quit_requested.connect(self.quit_application)

        has_credentials = (
            self.account_manager is None
            or self.account_manager.has_stored_credentials()
        )
        if self.device_manager is None:
            self.devices_page.status_label.setText("尚未连接设备服务")
        elif not has_credentials:
            self.pages.setCurrentWidget(self.login_page)
            self._set_navigation(None)
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
            if self.settings_manager.refresh_interval > 0:
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
            self._flush_operation_refreshes()

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
            self._schedule_operation_refresh(did)

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
        self._set_navigation(self.devices_button)

    def show_favorites_page(self) -> None:
        self.pages.setCurrentWidget(self.favorites_page)
        self._set_navigation(self.favorites_button)

    def show_settings_page(self) -> None:
        self.pages.setCurrentWidget(self.settings_page)
        self._set_navigation(self.settings_button)

    def _set_navigation(self, selected: QPushButton | None) -> None:
        for button in (
            self.devices_button,
            self.favorites_button,
            self.settings_button,
        ):
            button.setChecked(button is selected)

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
        self._set_navigation(None)
        self.refresh_states({did})

    def change_theme(self, value: str) -> None:
        self.settings_manager.theme = value
        if self.theme_service is not None:
            self.theme_service.apply(value)
        else:
            self.setStyleSheet(load_stylesheet("dark" if value == "dark" else "light"))
        self.settings_page.show_status("主题设置已保存")

    def change_refresh_interval(self, seconds: int) -> None:
        self.settings_manager.refresh_interval = seconds
        self.refresh_timer.stop()
        if seconds > 0:
            self.refresh_timer.setInterval(seconds * 1_000)
            if self._devices_loaded and self.state_manager is not None:
                self.refresh_timer.start()
        self.settings_page.show_status(
            "已改为手动刷新" if seconds == 0 else f"每 {seconds} 秒刷新一次"
        )

    def change_startup(self, enabled: bool) -> None:
        if self.startup_service is None:
            self._restore_startup_checkbox()
            self.settings_page.show_status("当前环境不支持开机启动")
            return
        try:
            self.startup_service.set_enabled(enabled)
            if self.startup_service.is_enabled() is not enabled:
                raise RuntimeError("Windows 未确认启动项写入")
            self.settings_manager.startup_enabled = enabled
            self.settings_page.show_status("开机启动设置已保存")
        except Exception as error:
            self._restore_startup_checkbox()
            self.settings_page.show_status(f"开机启动设置失败：{error}")

    def _restore_startup_checkbox(self) -> None:
        checkbox = self.settings_page.startup_checkbox
        checkbox.blockSignals(True)
        checkbox.setChecked(self.settings_manager.startup_enabled)
        checkbox.blockSignals(False)

    def change_advanced_mode(self, enabled: bool) -> None:
        self.settings_manager.advanced_mode = enabled
        self.device_detail_page.set_advanced_mode(enabled)
        self.settings_page.show_status("高级模式设置已保存")

    def relogin(self) -> None:
        if self.account_manager is None:
            return
        try:
            self.account_manager.logout()
        except Exception as error:
            self.settings_page.show_status(f"无法清除登录状态：{error}")
            return
        self._invalidate_login_attempt()
        self.begin_login()

    def logout(self) -> None:
        if self.account_manager is None:
            return
        try:
            self.account_manager.logout()
        except Exception as error:
            self.settings_page.show_status(f"退出账号失败：{error}")
            return
        self._invalidate_login_attempt()
        self.refresh_timer.stop()
        self._devices_loaded = False
        self.devices_page.set_devices(())
        self.favorites_page.set_devices(())
        self.pages.setCurrentWidget(self.login_page)
        self._set_navigation(None)
        self.login_page.status_label.setText("账号已退出，可重新生成二维码登录")
        self.login_page.set_loading(False)

    def begin_login(self) -> None:
        if self.account_manager is None or self._login_in_progress:
            return
        self._login_attempt += 1
        attempt = self._login_attempt
        self._login_in_progress = True
        self.pages.setCurrentWidget(self.login_page)
        self._set_navigation(None)
        self.login_page.set_loading(True)
        self.login_page.prepare_login()
        self._run_background(
            self.account_manager.begin_login,
            on_result=lambda qr_path: self._on_login_started(attempt, qr_path),
            on_error=lambda error: self._on_login_failed(attempt, error),
        )

    def _on_login_started(self, attempt: int, qr_path) -> None:
        if attempt != self._login_attempt:
            return
        if qr_path is None:
            self._on_login_complete(attempt, None)
            return
        if not self.login_page.show_qr(qr_path):
            self._login_in_progress = False
            return
        self._run_background(
            self.account_manager.complete_login,
            on_result=lambda result: self._on_login_complete(attempt, result),
            on_error=lambda error: self._on_login_failed(attempt, error),
        )

    def _on_login_complete(self, attempt: int, _result: Any) -> None:
        if attempt != self._login_attempt:
            return
        self._login_in_progress = False
        self.login_page.set_loading(False)
        self.show_devices_page()
        self.refresh_devices()

    def _on_login_failed(self, attempt: int, error: Exception) -> None:
        if attempt != self._login_attempt:
            return
        self._login_in_progress = False
        self.login_page.show_error(str(error))

    def _invalidate_login_attempt(self) -> None:
        self._login_attempt += 1
        self._login_in_progress = False

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
            self._schedule_operation_refresh(did)

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
            self._schedule_operation_refresh(did)

        def fail(error: Exception) -> None:
            self.device_detail_page.finish_action(name, False, str(error))

        self._run_background(
            self.device_manager.run_action,
            did,
            name,
            on_result=complete,
            on_error=fail,
        )

    def _schedule_operation_refresh(self, did: str) -> None:
        """Refresh the operated device after cloud state has had time to settle."""
        QTimer.singleShot(
            POST_OPERATION_REFRESH_DELAY_MS,
            lambda: self._queue_operation_refresh(did),
        )

    def _queue_operation_refresh(self, did: str) -> None:
        self._pending_operation_refresh_dids.add(did)
        self._flush_operation_refreshes()

    def _flush_operation_refreshes(self) -> None:
        if self._state_refresh_in_progress or not self._pending_operation_refresh_dids:
            return
        dids = set(self._pending_operation_refresh_dids)
        self._pending_operation_refresh_dids.clear()
        self.refresh_states(dids)

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
