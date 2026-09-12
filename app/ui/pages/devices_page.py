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
    favorite_requested = Signal(str, bool)

    def __init__(self, parent=None, *, group_by_room: bool = True) -> None:
        super().__init__(parent)
        self.setObjectName("devicesPage")
        self._group_by_room = group_by_room
        self._room_filter: tuple[str, str] | None = None
        self._room_filter_title = ""
        self._devices: tuple[BaseDevice, ...] = ()
        self._cards: dict[str, DeviceCard] = {}
        self._room_headers: dict[tuple[str, str], QLabel] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        header = QHBoxLayout()
        title_block = QVBoxLayout()
        self.title_label = QLabel("我的设备")
        self.title_label.setObjectName("pageTitle")
        self.status_label = QLabel("尚未同步")
        self.status_label.setObjectName("pageStatus")
        title_block.addWidget(self.title_label)
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
        self.scroll_area.setObjectName("deviceScroll")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        self.scroll_area.viewport().setObjectName("deviceViewport")
        self.scroll_content = QWidget()
        self.scroll_content.setObjectName("deviceCanvas")
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

    @property
    def room_headers(self) -> dict[tuple[str, str], QLabel]:
        return dict(self._room_headers)

    @property
    def room_filter(self) -> tuple[str, str] | None:
        return self._room_filter

    def set_room_filter(
        self,
        room_filter: tuple[str, str] | None,
        title: str = "",
    ) -> None:
        self._room_filter = room_filter
        self._room_filter_title = title
        self.title_label.setText(title or "我的设备")
        self._apply_filter()

    def set_devices(self, devices: tuple[BaseDevice, ...]) -> None:
        self._devices = devices
        existing = self._cards
        updated: dict[str, DeviceCard] = {}
        for device in devices:
            card = existing.pop(device.did, None)
            if card is None:
                card = DeviceCard(device, self.scroll_content)
                card.quick_switch_requested.connect(self.quick_switch_requested)
                card.detail_requested.connect(self.detail_requested)
                card.favorite_requested.connect(self.favorite_requested)
            else:
                card.update_device(device)
            updated[device.did] = card
        for card in existing.values():
            card.hide()
            card.deleteLater()
        self._cards = updated
        valid_room_keys = {self.room_key(device) for device in devices}
        for key in set(self._room_headers) - valid_room_keys:
            header = self._room_headers.pop(key)
            header.hide()
            header.deleteLater()
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

    def finish_quick_switch(
        self,
        did: str,
        *,
        success: bool,
        error_message: str | None = None,
    ) -> None:
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
            matches_room = (
                self._room_filter is None
                or self.room_key(device) == self._room_filter
            )
            matches = (
                matches_room
                and (
                    not query
                    or query in device.name.casefold()
                    or query in device.model.casefold()
                )
            )
            card.setVisible(matches)
            if matches:
                visible_cards.append(card)
        self.empty_label.setText("没有匹配的设备" if self._devices else "暂无设备")
        self.empty_label.setVisible(not visible_cards)
        self._relayout_cards(visible_cards)

    def _relayout_cards(self, cards: list[DeviceCard] | None = None) -> None:
        cards = cards if cards is not None else [
            card for card in self._cards.values() if not card.isHidden()
        ]
        while self.grid.count():
            self.grid.takeAt(0)
        for header in self._room_headers.values():
            header.hide()
        if not cards:
            self.grid.addWidget(self.empty_label, 0, 0)
            return
        available_width = max(self.scroll_area.viewport().width() - 8, 250)
        columns = max(1, available_width // 280)
        if not self._group_by_room:
            for index, card in enumerate(cards):
                self.grid.addWidget(card, index // columns, index % columns)
            for column in range(columns):
                self.grid.setColumnStretch(column, 1)
            return

        groups: dict[tuple[str, str], list[DeviceCard]] = {}
        for card in cards:
            groups.setdefault(self.room_key(card.device), []).append(card)

        row = 0
        for key, room_cards in sorted(groups.items(), key=self._room_sort_key):
            room_cards.sort(key=lambda card: (not card.device.favorite, card.device.name))
            header = self._room_headers.get(key)
            if header is None:
                header = QLabel(self.scroll_content)
                header.setObjectName("roomHeader")
                self._room_headers[key] = header
            header.setText(self.room_title(room_cards[0].device))
            header.show()
            self.grid.addWidget(header, row, 0, 1, columns)
            row += 1
            for index, card in enumerate(room_cards):
                self.grid.addWidget(card, row + index // columns, index % columns)
            row += (len(room_cards) + columns - 1) // columns
        for column in range(columns):
            self.grid.setColumnStretch(column, 1)

    @staticmethod
    def room_key(device: BaseDevice) -> tuple[str, str]:
        home = device.home_id or device.home_name or "__unknown_home__"
        room = device.room_id or "__unassigned_room__"
        return home, room

    @staticmethod
    def room_title(device: BaseDevice) -> str:
        home = device.home_name or "未知家庭"
        room = device.room_name or "未分配房间"
        return f"{home} · {room}"

    def _room_sort_key(
        self,
        item: tuple[tuple[str, str], list[DeviceCard]],
    ) -> tuple[str, bool, str]:
        device = item[1][0].device
        return (
            device.home_name.casefold(),
            not bool(device.room_id),
            device.room_name.casefold(),
        )
