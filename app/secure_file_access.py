"""All document filesystem operations are confined to an open root directory fd.

Each path component is opened relative to the previous directory with O_NOFOLLOW.
This avoids the check/open race and works on Linux without requiring openat2.
The OS sandbox in run.sh is still required to confine the whole process.
"""
from __future__ import annotations

import logging
import os
import stat
from dataclasses import dataclass

LOG = logging.getLogger(__name__)
TEXT_EXTENSIONS = frozenset({
    ".txt", ".text", ".log", ".csv", ".tsv", ".json", ".jsonl", ".xml",
    ".yaml", ".yml", ".ini", ".cfg", ".conf", ".toml", ".rst", ".tex",
    ".sql", ".py", ".sh", ".css", ".js",
})
IMAGE_EXTENSIONS = frozenset({
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif",
    ".tiff", ".ico", ".pbm", ".pgm", ".ppm", ".svg",
})
OFFICE_EXTENSIONS = frozenset({".docx", ".odt"})
SUPPORTED = frozenset({".md", ".pdf", ".html", ".htm", ".rtf"}) | TEXT_EXTENSIONS | IMAGE_EXTENSIONS | OFFICE_EXTENSIONS
MAX_DOCUMENT = 128 * 1024 * 1024


class AccessDenied(ValueError):
    pass


@dataclass(frozen=True)
class Entry:
    path: str
    directory: bool


class SecureFileAccess:
    def __init__(self, root: str):
        canonical = os.path.realpath(root)
        if not os.path.isdir(canonical):
            raise AccessDenied(f"Kein lesbares Verzeichnis: {root}")
        self._root = canonical
        self._fd = os.open(canonical, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW)

    @property
    def root(self) -> str:
        return self._root

    def close(self) -> None:
        if self._fd >= 0:
            os.close(self._fd)
            self._fd = -1

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def _parts(self, relative: str, allow_root: bool = False) -> list[str]:
        if not isinstance(relative, str) or "\x00" in relative or relative.startswith("/"):
            return self._deny(relative)
        if relative == "" and allow_root:
            return []
        parts = relative.split("/")
        if not parts or any(p in ("", ".", "..") for p in parts):
            return self._deny(relative)
        return parts

    @staticmethod
    def _deny(path):
        LOG.warning("Abgewiesener Dateizugriff: %r", path)
        raise AccessDenied(f"Unzulässiger Pfad: {path!r}")

    def _dir_fd(self, parts: list[str]) -> int:
        fd = os.dup(self._fd)
        try:
            for part in parts:
                new = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
                os.close(fd)
                fd = new
            return fd
        except (OSError, ValueError) as exc:
            os.close(fd)
            LOG.warning("Abgewiesener Verzeichniszugriff %r: %s", parts, exc)
            raise AccessDenied("Verzeichnis nicht zugänglich") from exc

    def list_dir(self, relative: str = "") -> list[Entry]:
        parts = self._parts(relative, allow_root=True)
        fd = self._dir_fd(parts)
        result = []
        try:
            with os.scandir(fd) as entries:
                for item in entries:
                    try:
                        st = item.stat(follow_symlinks=False)
                    except OSError:
                        continue
                    if stat.S_ISLNK(st.st_mode):
                        continue
                    path = f"{relative}/{item.name}" if relative else item.name
                    if stat.S_ISDIR(st.st_mode):
                        result.append(Entry(path, True))
                    elif stat.S_ISREG(st.st_mode) and os.path.splitext(item.name)[1].lower() in SUPPORTED:
                        result.append(Entry(path, False))
        finally:
            os.close(fd)
        return sorted(result, key=lambda e: (not e.directory, e.path.casefold()))

    def read_bytes(self, relative: str, limit: int = MAX_DOCUMENT) -> bytes:
        parts = self._parts(relative)
        if os.path.splitext(parts[-1])[1].lower() not in SUPPORTED:
            return self._deny(relative)
        parent = self._dir_fd(parts[:-1])
        try:
            try:
                fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=parent)
            except OSError as exc:
                LOG.warning("Abgewiesener Dateizugriff %r: %s", relative, exc)
                raise AccessDenied("Datei nicht zugänglich") from exc
        finally:
            os.close(parent)
        try:
            st = os.fstat(fd)
            if not stat.S_ISREG(st.st_mode) or st.st_size > limit:
                return self._deny(relative)
            data = bytearray()
            while len(data) <= limit:
                chunk = os.read(fd, min(1024 * 1024, limit + 1 - len(data)))
                if not chunk:
                    return bytes(data)
                data.extend(chunk)
            return self._deny(relative)
        finally:
            os.close(fd)

    def read_text(self, relative: str) -> str:
        return self.read_bytes(relative, limit=16 * 1024 * 1024).decode("utf-8", errors="replace")

    def read_asset(self, relative: str, limit: int = 16 * 1024 * 1024) -> bytes:
        """Read an image for a document, using identical fd checks."""
        parts = self._parts(relative)
        if os.path.splitext(parts[-1])[1].lower() not in IMAGE_EXTENSIONS:
            return self._deny(relative)
        parent = self._dir_fd(parts[:-1])
        try:
            try:
                fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=parent)
            except OSError as exc:
                raise AccessDenied("Bild nicht zugänglich") from exc
        finally:
            os.close(parent)
        try:
            st = os.fstat(fd)
            if not stat.S_ISREG(st.st_mode) or st.st_size > limit:
                return self._deny(relative)
            result = bytearray()
            while len(result) <= limit:
                chunk = os.read(fd, min(1024 * 1024, limit + 1 - len(result)))
                if not chunk:
                    return bytes(result)
                result.extend(chunk)
            return self._deny(relative)
        finally:
            os.close(fd)
