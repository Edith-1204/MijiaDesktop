"""Capability-driven property controls used by the generic device UI."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.models.capability import DeviceCapability


class BasePropertyWidget(QFrame):
    """Common presentation and pending-state behavior for one property."""

    change_requested = Signal(str, object)

    def __init__(self, capability: DeviceCapability, parent=None) -> None:
        super().__init__(parent)
        self.capability = capability
        self._confirmed_value = capability.value
        self._pending = False
        self.setObjectName("propertyRow")

        self.root_layout = QHBoxLayout(self)
        self.root_layout.setContentsMargins(14, 11, 14, 11)
        self.root_layout.setSpacing(14)
        labels = QVBoxLayout()
        self.name_label = QLabel(capability.description or capability.name)
        self.name_label.setObjectName("propertyName")
        self.identifier_label = QLabel(capability.name)
        self.identifier_label.setObjectName("propertyIdentifier")
        labels.addWidget(self.name_label)
        labels.addWidget(self.identifier_label)
        self.root_layout.addLayout(labels, 1)
        self.editor_container = QWidget()
        self.editor_layout = QHBoxLayout(self.editor_container)
        self.editor_layout.setContentsMargins(0, 0, 0, 0)
        self.editor_layout.setSpacing(8)
        self.root_layout.addWidget(self.editor_container)

    def request_change(self, value: Any) -> None:
        if self._pending:
            return
        self.set_pending(True)
        self.change_requested.emit(self.capability.name, value)

    def finish(self, success: bool, value: Any = None) -> None:
        if success:
            if value is not None:
                self._set_editor_value(value)
            self._confirmed_value = self._editor_value()
            self.capability.value = self._confirmed_value
        else:
            self._set_editor_value(self._confirmed_value)
        self.set_pending(False)

    def set_pending(self, pending: bool) -> None:
        self._pending = pending
        self.editor_container.setEnabled(not pending)
        self.setProperty("pending", pending)
        self.style().unpolish(self)
        self.style().polish(self)

    def _editor_value(self) -> Any:
        return self.capability.value

    def _set_editor_value(self, value: Any) -> None:
        self.capability.value = value


class BooleanPropertyWidget(BasePropertyWidget):
    def __init__(self, capability: DeviceCapability, parent=None) -> None:
        super().__init__(capability, parent)
        self.editor = QCheckBox("开启")
        self.editor.setObjectName("booleanEditor")
        self.editor.setChecked(bool(capability.value))
        self.editor.setText("开启" if bool(capability.value) else "关闭")
        self.editor.toggled.connect(self._on_toggled)
        self.editor_layout.addWidget(self.editor)

    def _on_toggled(self, checked: bool) -> None:
        self.editor.setText("开启" if checked else "关闭")
        self.request_change(checked)

    def _editor_value(self) -> bool:
        return self.editor.isChecked()

    def _set_editor_value(self, value: Any) -> None:
        self.editor.blockSignals(True)
        self.editor.setChecked(bool(value))
        self.editor.setText("开启" if bool(value) else "关闭")
        self.editor.blockSignals(False)


class SliderPropertyWidget(BasePropertyWidget):
    def __init__(self, capability: DeviceCapability, parent=None) -> None:
        super().__init__(capability, parent)
        self._scale = self._calculate_scale(capability.step)
        self.editor = QSlider(Qt.Orientation.Horizontal)
        self.editor.setObjectName("numberSlider")
        minimum = capability.min_value if capability.min_value is not None else 0
        maximum = capability.max_value if capability.max_value is not None else 100
        self.editor.setMinimum(self._encode(minimum))
        self.editor.setMaximum(self._encode(maximum))
        step = capability.step if capability.step is not None else 1
        self.editor.setSingleStep(max(1, self._encode(step)))
        self.editor.setMinimumWidth(150)
        self.value_label = QLabel()
        self.value_label.setObjectName("propertyValue")
        initial = capability.value
        if initial is None:
            initial = capability.min_value if capability.min_value is not None else 0
        self._set_editor_value(initial)
        self.editor.valueChanged.connect(self._update_value_label)
        self.editor.sliderReleased.connect(lambda: self.request_change(self._editor_value()))
        self.editor_layout.addWidget(self.editor)
        self.editor_layout.addWidget(self.value_label)

    @staticmethod
    def _calculate_scale(step: int | float | None) -> int:
        if step is None:
            return 1
        exponent = max(0, -Decimal(str(step)).as_tuple().exponent)
        return 10**exponent

    def _encode(self, value: int | float) -> int:
        return round(float(value) * self._scale)

    def _decode(self, value: int) -> int | float:
        decoded = value / self._scale
        if self.capability.value_type in {"int", "uint"}:
            return int(decoded)
        return decoded

    def _editor_value(self) -> int | float:
        return self._decode(self.editor.value())

    def _set_editor_value(self, value: Any) -> None:
        self.editor.blockSignals(True)
        self.editor.setValue(self._encode(value))
        self.editor.blockSignals(False)
        self._update_value_label()

    def _update_value_label(self) -> None:
        value = self._editor_value()
        suffix = f" {self.capability.unit}" if self.capability.unit else ""
        self.value_label.setText(f"{value:g}{suffix}")


class NumberPropertyWidget(BasePropertyWidget):
    def __init__(self, capability: DeviceCapability, parent=None) -> None:
        super().__init__(capability, parent)
        if capability.value_type in {"int", "uint"}:
            editor: QSpinBox | QDoubleSpinBox = QSpinBox()
            editor.setRange(-2_147_483_648, 2_147_483_647)
        else:
            editor = QDoubleSpinBox()
            editor.setDecimals(4)
            editor.setRange(-1_000_000_000, 1_000_000_000)
        self.editor = editor
        self.editor.setObjectName("numberEditor")
        if capability.step is not None:
            self.editor.setSingleStep(capability.step)
        if capability.unit:
            self.editor.setSuffix(f" {capability.unit}")
        self._set_editor_value(capability.value or 0)
        self.editor.editingFinished.connect(lambda: self.request_change(self._editor_value()))
        self.editor_layout.addWidget(self.editor)

    def _editor_value(self) -> int | float:
        return self.editor.value()

    def _set_editor_value(self, value: Any) -> None:
        self.editor.blockSignals(True)
        self.editor.setValue(value)
        self.editor.blockSignals(False)


class EnumPropertyWidget(BasePropertyWidget):
    def __init__(self, capability: DeviceCapability, parent=None) -> None:
        super().__init__(capability, parent)
        self.editor = QComboBox()
        self.editor.setObjectName("enumEditor")
        for value, description in capability.enum_values.items():
            self.editor.addItem(description, value)
        self._set_editor_value(capability.value)
        self.editor.currentIndexChanged.connect(self._on_changed)
        self.editor_layout.addWidget(self.editor)

    def _on_changed(self, index: int) -> None:
        if index >= 0:
            self.request_change(self.editor.itemData(index))

    def _editor_value(self) -> Any:
        return self.editor.currentData()

    def _set_editor_value(self, value: Any) -> None:
        self.editor.blockSignals(True)
        index = self.editor.findData(value)
        self.editor.setCurrentIndex(index if index >= 0 else 0)
        self.editor.blockSignals(False)


class ReadOnlyPropertyWidget(BasePropertyWidget):
    def __init__(self, capability: DeviceCapability, parent=None) -> None:
        super().__init__(capability, parent)
        self.editor = QLabel()
        self.editor.setObjectName("readOnlyValue")
        self._set_editor_value(capability.value)
        self.editor_layout.addWidget(self.editor)

    def _editor_value(self) -> Any:
        return self.capability.value

    def _set_editor_value(self, value: Any) -> None:
        self.capability.value = value
        if value is None:
            text = "—"
        elif self.capability.enum_values and value in self.capability.enum_values:
            text = self.capability.enum_values[value]
        elif isinstance(value, bool):
            text = "开启" if value else "关闭"
        else:
            text = str(value)
        if self.capability.unit and value is not None:
            text = f"{text} {self.capability.unit}"
        self.editor.setText(text)


def create_property_widget(capability: DeviceCapability) -> BasePropertyWidget:
    """Map one capability to the most appropriate generic Qt control."""
    if not capability.writable:
        return ReadOnlyPropertyWidget(capability)
    if capability.is_enum:
        return EnumPropertyWidget(capability)
    if capability.value_type == "bool":
        return BooleanPropertyWidget(capability)
    if capability.value_type in {"int", "uint", "float"} and capability.has_range:
        return SliderPropertyWidget(capability)
    if capability.value_type in {"int", "uint", "float"}:
        return NumberPropertyWidget(capability)
    return ReadOnlyPropertyWidget(capability)
