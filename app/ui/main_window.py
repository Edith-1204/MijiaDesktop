"""The primary application window."""

from PySide6.QtCore import QSize
from PySide6.QtWidgets import QMainWindow


class MainWindow(QMainWindow):
    """Minimal Phase 0 window used to verify the desktop shell."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Mijia Desktop")
        self.resize(QSize(960, 640))
        self.setMinimumSize(QSize(720, 480))

