"""Favorite-device view."""

from __future__ import annotations

from app.models.device import BaseDevice
from app.ui.pages.devices_page import DevicesPage


class FavoritesPage(DevicesPage):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.title_label.setText("收藏设备")
        self.search_input.setPlaceholderText("搜索收藏设备")

    def set_devices(self, devices: tuple[BaseDevice, ...]) -> None:
        super().set_devices(tuple(device for device in devices if device.favorite))
        if not self._devices:
            self.empty_label.setText("还没有收藏设备")

    def _apply_filter(self) -> None:
        super()._apply_filter()
        if not self._devices and not self.search_input.text().strip():
            self.empty_label.setText("还没有收藏设备")
