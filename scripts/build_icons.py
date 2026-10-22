"""Render the native SVG icon sources and export the macOS icon container."""

from pathlib import Path

from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer


def main() -> None:
    directory = Path(__file__).resolve().parents[1] / "resources" / "icons"
    renderer = QSvgRenderer(str(directory / "mijia-macos.svg"))
    if not renderer.isValid():
        raise RuntimeError("Invalid macOS icon SVG")
    image = QImage(1024, 1024, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    renderer.render(painter)
    painter.end()
    path = directory / "mijia-macos.png"
    if not image.save(str(path)):
        raise RuntimeError("Cannot save macOS icon")
    with Image.open(path) as rendered:
        rendered.save(directory / "mijia.icns", format="ICNS")


if __name__ == "__main__":
    main()
