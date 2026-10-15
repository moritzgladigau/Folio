#!/usr/bin/env python3
"""Regenerate PNG icon sizes from the SVG master using PySide6."""
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer


def main():
    app = QGuiApplication([])
    directory = Path(__file__).resolve().parent
    renderer = QSvgRenderer(str(directory / "folio-readonly.svg"))
    if not renderer.isValid():
        raise RuntimeError("SVG-Icon ist ungültig")
    for size in (32, 64, 128, 256):
        image = QImage(size * 4, size * 4, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        renderer.render(painter)
        painter.end()
        output = image.scaled(size, size, Qt.AspectRatioMode.IgnoreAspectRatio,
                              Qt.TransformationMode.SmoothTransformation)
        if not output.save(str(directory / f"folio-readonly-{size}.png")):
            raise RuntimeError(f"PNG mit {size} px konnte nicht geschrieben werden")
    del app


if __name__ == "__main__":
    main()
