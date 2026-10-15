"""Decode raster images from guarded memory, without direct file access."""
from __future__ import annotations

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, Qt
from PySide6.QtGui import QImageReader, QPixmap
from PySide6.QtWidgets import QLabel, QScrollArea

from .secure_file_access import AccessDenied, SecureFileAccess


class ImageViewer(QScrollArea):
    def __init__(self, access: SecureFileAccess, parent=None):
        super().__init__(parent)
        self.access = access
        self.label = QLabel()
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWidget(self.label)
        self.scale = 1.0
        self.pixmap = QPixmap()

    def show_document(self, path: str):
        data = QByteArray(self.access.read_asset(path))
        buffer = QBuffer()
        buffer.setData(data)
        buffer.open(QIODevice.OpenModeFlag.ReadOnly)
        QImageReader.setAllocationLimit(160)
        reader = QImageReader(buffer)
        reader.setAutoTransform(True)
        size = reader.size()
        if size.isValid() and size.width() * size.height() > 40_000_000:
            raise AccessDenied("Bildauflösung ist zu groß")
        image = reader.read()
        if image.isNull() or image.width() * image.height() > 40_000_000:
            raise AccessDenied("Bildformat nicht lesbar oder Bildauflösung zu groß")
        self.pixmap = QPixmap.fromImage(image)
        self.scale = 1.0
        self._update_size()

    def set_zoom(self, factor: float):
        self.scale = max(0.1, min(4.0, factor))
        self._update_size()

    def _update_size(self):
        if not self.pixmap.isNull():
            self.label.setPixmap(self.pixmap)
            self.label.resize(self.pixmap.size() * self.scale)
            self.label.setScaledContents(True)
