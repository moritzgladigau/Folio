#!/usr/bin/env python3
"""Folio entry point. run.sh starts this inside Bubblewrap."""
import argparse
import os
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from app.secure_file_access import AccessDenied, SecureFileAccess
from app.web_viewer import register_scheme


def main():
    parser = argparse.ArgumentParser(description="Folio · ReadOnly Dokumentenbrowser")
    parser.add_argument("root", nargs="?")
    parser.add_argument("--choose", action="store_true", help="Ordner vor Sandbox-Start auswählen")
    args = parser.parse_args()
    if args.choose:
        app = QApplication(sys.argv[:1])
        app.setWindowIcon(QIcon(os.path.join(os.path.dirname(__file__), "assets", "folio-readonly-256.png")))
        folder = QFileDialog.getExistingDirectory(None, "Dokumentenordner auswählen")
        if folder:
            print(folder, end="")
            return 0
        return 2
    if not args.root:
        parser.error("Stammverzeichnis fehlt; bitte run.sh verwenden")
    register_scheme()
    app = QApplication(sys.argv[:1])
    app.setWindowIcon(QIcon(os.path.join(os.path.dirname(__file__), "assets", "folio-readonly-256.png")))
    try:
        access = SecureFileAccess(args.root)
    except (AccessDenied, OSError) as exc:
        QMessageBox.critical(None, "Folio", str(exc))
        return 1
    from app.main_window import MainWindow
    window = MainWindow(access)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
