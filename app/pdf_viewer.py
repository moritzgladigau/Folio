"""Qt PDF renderer backed by an in-memory, read-only QBuffer."""
from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPointF, Signal
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPdfWidgets import QPdfView
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from .secure_file_access import SecureFileAccess


class PdfViewer(QWidget):
    zoomChanged = Signal(float)

    def __init__(self, access: SecureFileAccess, parent=None):
        super().__init__(parent)
        self.access = access
        self.document = QPdfDocument(self)
        self.document.statusChanged.connect(self._status_changed)
        self.buffer = QBuffer(self)
        self.view = QPdfView(self)
        self.view.setDocument(self.document)
        self.view.setPageMode(QPdfView.PageMode.MultiPage)
        self.view.setZoomMode(QPdfView.ZoomMode.Custom)
        self.view.setZoomFactor(1.0)
        self.page_label = QLabel("0 / 0")
        prev_btn = QPushButton("‹ Seite")
        next_btn = QPushButton("Seite ›")
        prev_btn.clicked.connect(lambda: self.move_page(-1))
        next_btn.clicked.connect(lambda: self.move_page(1))
        row = QHBoxLayout()
        row.addWidget(prev_btn)
        row.addWidget(self.page_label)
        row.addWidget(next_btn)
        row.addStretch()
        layout = QVBoxLayout(self)
        layout.addLayout(row)
        layout.addWidget(self.view)
        self.page = 0

    def show_document(self, path: str):
        self.document.close()
        self.buffer.close()
        self.buffer.setData(QByteArray(self.access.read_bytes(path)))
        self.buffer.open(QIODevice.OpenModeFlag.ReadOnly)
        self.document.load(self.buffer)
        self.page = 0
        self._update_label()

    def move_page(self, delta: int):
        self.page = max(0, min(self.document.pageCount() - 1, self.page + delta))
        self._update_label()
        self.view.pageNavigator().jump(self.page, QPointF(), self.view.zoomFactor())

    def _update_label(self):
        self.page_label.setText(f"{self.page + 1 if self.document.pageCount() else 0} / {self.document.pageCount()}")

    def _status_changed(self, status):
        if status == QPdfDocument.Status.Error:
            self.page_label.setText("PDF beschädigt oder nicht lesbar")
        elif status == QPdfDocument.Status.Ready:
            self._update_label()
