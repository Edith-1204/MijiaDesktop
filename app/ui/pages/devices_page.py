"""All-devices page with search and responsive cards."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.models.device import BaseDevice
from app.ui.widgets.device_card import DeviceCard


class DevicesPage(QWidget):
    refresh_requested = Signal()
    quick_switch_requested = Signal(str, bool)
    detail_requested = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._devices: tuple[BaseDevice, ...] = ()
        self._cards: dict[str, DeviceCard] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        header = QHBoxLayout()
        title_block = QVBoxLayout()
        title = QLabel("我的设备")
        title.setObjectName("pageTitle")
        self.status_label = QLabel("尚未同步")
        self.status_label.setObjectName("pageStatus")
        title_block.addWidget(title)
        title_block.addWidget(self.status_label)
        header.addLayout(title_block)
        header.addStretch(1)
        self.refresh_button = QPushButton("刷新")
        self.refresh_button.setObjectName("refreshButton")
        self.refresh_button.clicked.connect(self.refresh_requested)
        header.addWidget(self.refresh_button)
        root.addLayout(header)

        self.search_input = QLineEdit()
        self.search_input.setObjectName("deviceSearch")
        self.search_input.setPlaceholderText("搜索设备名称或型号")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._apply_filter)
        root.addWidget(self.search_input)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        self.scroll_content = QWidget()
        self.grid = QGridLayout(self.scroll_content)
        self.grid.setContentsMargins(0, 0, 8, 0)
        self.grid.setHorizontalSpacing(14)
        self.grid.setVerticalSpacing(14)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_area.setWidget(self.scroll_content)
        self.scroll_area.viewport().installEventFilter(self)
        root.addWidget(self.scroll_area, 1)

        self.empty_label = QLabel("暂无设备")
        self.empty_label.setObjectName("emptyState")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.grid.addWidget(self.empty_label, 0, 0)

    @property
    def cards(self) -> dict[str, DeviceCard]:
        return dict(self._cards)

    def set_devices(self, devices: tuple[BaseDevice, ...]) -> None:
        self._devices = devices
        for card in self._cards.values():
            card.deleteLater()
        self._cards.clear()
        for device in devices:
            card = DeviceCard(device)
            card.quick_switch_requested.connect(self.quick_switch_requested)
            card.detail_requested.connect(self.detail_requested)
            self._cards[device.did] = card
        self.status_label.setText(f"共 {len(devices)} 台设备")
        self._apply_filter()

    def set_loading(self, loading: bool) -> None:
        self.refresh_button.setEnabled(not loading)
        self.refresh_button.setText("正在同步…" if loading else "刷新")
        if loading:
            self.status_label.setText("正在从米家同步设备…")

    def show_error(self, message: str) -> None:
        self.status_label.setText(f"同步失败：{message}")

    def set_state_loading(self, loading: bool) -> None:
        self.refresh_button.setEnabled(not loading)
        self.refresh_button.setText("正在刷新…" if loading else "刷新")
        if loading:
            self.status_label.setText("正在刷新设备状态…")

    def update_states(self, devices: tuple[BaseDevice, ...]) -> None:
        self._devices = devices
        for device in devices:
            card = self._cards.get(device.did)
            if card is not None:
                card.update_device(device)
        self.status_label.setText(f"状态已刷新 · {datetime.now():%H:%M:%S}")

    def show_refresh_error(self, message: str) -> None:
        self.status_label.setText(f"状态刷新失败：{message}")

    def begin_quick_switch(self, did: str, desired_state: bool) -> None:
        card = self._cards.get(did)
        if card is not None:
            card.set_pending(True, desired_state)

    def finish_quick_switch(self, did: str, *, success: bool, error_message: str | None = None) -> None:
        card = self._cards.get(did)
        if card is None:
            return
        card.set_pending(False)
        if success:
            self.status_label.setText(f"已更新：{card.device.name}")
        elif error_message:
            self.status_label.setText(f"控制失败：{error_message}")

    def eventFilter(self, watched, event) -> bool:
        if watched is self.scroll_area.viewport() and event.type() == QEvent.Type.Resize:
            self._relayout_cards()
        return super().eventFilter(watched, event)

    def _apply_filter(self) -> None:
        query = self.search_input.text().strip().casefold()
        visible_cards = []
        for device in self._devices:
            card = self._cards[device.did]
            matches = not query or query in device.name.casefold() or query in device.model.casefold()
            card.setVisible(matches)
            if matches:
                visible_cards.append(card)
        self.empty_label.setText("没有匹配的设备" if self._devices else "暂无设备")
        self.empty_label.setVisible(not visible_cards)
        self._relayout_cards(visible_cards)

    def _relayout_cards(self, cards: list[DeviceCard] | None = None) -> None:
        cards = cards if cards is not None else [card for card in self._cards.values() if not card.isHidden()]
        while self.grid.count():
            self.grid.takeAt(0)
        if not cards:
            self.grid.addWidget(self.empty_label, 0, 0)
            return
        available_width = max(self.scroll_area.viewport().width() - 8, 250)
        columns = max(1, available_width // 280)
        for index, card in enumerate(cards):
            self.grid.addWidget(card, index // columns, index % columns)
        for column in range(columns):
            self.grid.setColumnStretch(column, 1)
