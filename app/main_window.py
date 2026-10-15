"""Read-only document browser window."""
from __future__ import annotations

import os

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QAction, QFont
from PySide6.QtWidgets import (
    QCheckBox, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox,
    QPlainTextEdit, QSplitter, QStackedWidget, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QWidget,
)

from .document_loader import document_kind, rtf_text
from .image_viewer import ImageViewer
from .navigation import Navigation
from .pdf_viewer import PdfViewer
from .secure_file_access import AccessDenied, SecureFileAccess, TEXT_EXTENSIONS, IMAGE_EXTENSIONS, OFFICE_EXTENSIONS
from .web_viewer import WebViewer


class MainWindow(QMainWindow):
    def __init__(self, access: SecureFileAccess):
        super().__init__()
        self.access = access
        self.nav = Navigation()
        self.setWindowTitle("Folio · ReadOnly Dokumentenbrowser")
        self.resize(1280, 800)
        self._build_ui()
        self._populate()
        if self.nav.documents:
            self.open_document(self.nav.documents[0])

    def _build_ui(self):
        toolbar = self.addToolBar("Navigation")
        toolbar.setMovable(False)
        for label, callback in (("← Zurück", self.back), ("Vorwärts →", self.forward),
                                ("↑ Vorheriges", lambda: self.adjacent(-1)),
                                ("Nächstes ↓", lambda: self.adjacent(1)),
                                ("Zoom +", lambda: self.zoom(1.2)),
                                ("Zoom −", lambda: self.zoom(1 / 1.2)),
                                ("100 %", self.reset_zoom)):
            action = QAction(label, self)
            action.triggered.connect(callback)
            toolbar.addAction(action)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        root_label = QLabel(self.access.root)
        root_label.setWordWrap(True)
        root_label.setObjectName("rootLabel")
        left_layout.addWidget(QLabel("STAMMVERZEICHNIS"))
        left_layout.addWidget(root_label)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Dateiname, Endung oder Pfad suchen …")
        self.search.textChanged.connect(self._filter)
        left_layout.addWidget(self.search)
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.itemActivated.connect(self._tree_open)
        self.tree.itemClicked.connect(self._tree_open)
        left_layout.addWidget(self.tree)
        splitter.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        self.title = QLabel("Kein Dokument")
        self.title.setObjectName("documentTitle")
        right_layout.addWidget(self.title)
        self.stack = QStackedWidget()
        self.web = WebViewer(self.access)
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        self.text.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.pdf = PdfViewer(self.access)
        self.image = ImageViewer(self.access)
        self.stack.addWidget(self.web)
        self.stack.addWidget(self.text)
        self.stack.addWidget(self.pdf)
        self.stack.addWidget(self.image)
        right_layout.addWidget(self.stack)
        options = QHBoxLayout()
        self.monospace = QCheckBox("Monospace für Text")
        self.monospace.setChecked(True)
        self.monospace.toggled.connect(self._set_text_font)
        options.addWidget(self.monospace)
        options.addStretch()
        right_layout.addLayout(options)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        self.setCentralWidget(splitter)

        self.status_name = QLabel("Kein Dokument")
        self.status_count = QLabel("0 Dokumente")
        self.status_root = QLabel(self.access.root)
        self.statusBar().addWidget(self.status_name)
        self.statusBar().addPermanentWidget(self.status_count)
        self.statusBar().addPermanentWidget(QLabel("ReadOnly Dokumentenbrowser"))
        self.statusBar().addPermanentWidget(self.status_root)
        self._set_text_font(True)
        self.setStyleSheet("""
            QMainWindow,QWidget{font-size:14px}QTreeWidget{border:0}QLineEdit{padding:8px;border-radius:6px}
            #documentTitle{font-size:20px;font-weight:600;padding:5px 10px}#rootLabel{font-size:12px;opacity:.8}
            QToolBar{spacing:6px;padding:5px}QStatusBar{padding:3px}
        """)

    def _populate(self):
        self.tree.clear()
        docs = []

        def add(parent, folder):
            try:
                entries = self.access.list_dir(folder)
            except AccessDenied:
                return
            for entry in entries:
                item = QTreeWidgetItem(parent, ["📁 " + os.path.basename(entry.path) if entry.directory else
                                                self._icon(entry.path) + " " + os.path.basename(entry.path)])
                item.setData(0, Qt.ItemDataRole.UserRole, entry.path)
                item.setData(0, Qt.ItemDataRole.UserRole + 1, entry.directory)
                if entry.directory:
                    add(item, entry.path)
                else:
                    docs.append(entry.path)

        add(self.tree, "")
        self.nav.documents = sorted(docs, key=str.casefold)
        self.status_count.setText(f"{len(docs)} Dokumente")
        self.tree.expandToDepth(0)

    @staticmethod
    def _icon(path):
        kind = document_kind(path)
        if kind in IMAGE_EXTENSIONS:
            return "▧"
        if kind in OFFICE_EXTENSIONS:
            return "▤"
        if kind in TEXT_EXTENSIONS or kind == ".rtf":
            return "≡"
        return {".md": "◆", ".pdf": "▣", ".html": "◈", ".htm": "◈"}.get(kind, "•")

    def _filter(self, query):
        query = query.casefold().strip()

        def show(item):
            path = item.data(0, Qt.ItemDataRole.UserRole)
            is_dir = item.data(0, Qt.ItemDataRole.UserRole + 1)
            child_visible = any(show(item.child(i)) for i in range(item.childCount()))
            visible = not query or (not is_dir and query in path.casefold()) or child_visible
            item.setHidden(not visible)
            if query and child_visible:
                item.setExpanded(True)
            return visible

        for i in range(self.tree.topLevelItemCount()):
            show(self.tree.topLevelItem(i))

    def _tree_open(self, item, _column):
        if not item.data(0, Qt.ItemDataRole.UserRole + 1):
            self.open_document(item.data(0, Qt.ItemDataRole.UserRole))

    def open_document(self, path, record=True):
        if path not in self.nav.documents:
            return
        try:
            kind = document_kind(path)
            if kind == ".pdf":
                self.pdf.show_document(path)
                self.stack.setCurrentWidget(self.pdf)
            elif kind in IMAGE_EXTENSIONS and kind != ".svg":
                self.image.show_document(path)
                self.stack.setCurrentWidget(self.image)
            elif kind in TEXT_EXTENSIONS or kind == ".rtf":
                self.text.setPlainText(rtf_text(self.access, path) if kind == ".rtf" else self.access.read_text(path))
                self.stack.setCurrentWidget(self.text)
            else:
                # WebEngine's scheme handler performs the secure read for every resource.
                self.web.show_document(path)
                self.stack.setCurrentWidget(self.web)
            if record:
                self.nav.visit(path)
            self.title.setText(os.path.basename(path))
            self.status_name.setText(path)
        except (AccessDenied, OSError) as exc:
            QMessageBox.warning(self, "Dokument nicht lesbar", str(exc))

    def back(self):
        path = self.nav.back()
        if path:
            self.open_document(path, False)

    def forward(self):
        path = self.nav.forward()
        if path:
            self.open_document(path, False)

    def adjacent(self, delta):
        path = self.nav.adjacent(delta)
        if path:
            self.open_document(path, False)

    def zoom(self, factor):
        current = self.stack.currentWidget()
        if current == self.web:
            self.web.setZoomFactor(max(.4, min(4, self.web.zoomFactor() * factor)))
        elif current == self.pdf:
            self.pdf.view.setZoomFactor(max(.4, min(4, self.pdf.view.zoomFactor() * factor)))
        elif current == self.image:
            self.image.set_zoom(self.image.scale * factor)
        else:
            font = self.text.font()
            font.setPointSizeF(max(7, min(36, font.pointSizeF() * factor)))
            self.text.setFont(font)

    def reset_zoom(self):
        self.web.setZoomFactor(1)
        self.pdf.view.setZoomFactor(1)
        self.image.set_zoom(1)
        self._set_text_font(self.monospace.isChecked())

    def _set_text_font(self, checked):
        font = QFont("DejaVu Sans Mono" if checked else "Sans Serif")
        font.setPointSize(11)
        self.text.setFont(font)

    def closeEvent(self, event):
        self.web.setUrl(QUrl("about:blank"))
        self.access.close()
        super().closeEvent(event)
