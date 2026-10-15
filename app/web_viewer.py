"""Offline WebEngine renderer with one guarded doc: scheme."""
from __future__ import annotations

import mimetypes
import os
from urllib.parse import unquote

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QUrl
from PySide6.QtWebEngineCore import (
    QWebEngineProfile, QWebEnginePage, QWebEngineSettings,
    QWebEngineUrlRequestInterceptor, QWebEngineUrlScheme,
    QWebEngineUrlSchemeHandler,
)
from PySide6.QtWebEngineWidgets import QWebEngineView

from .document_loader import markdown_html, html_document, error_html, resource_allowed, navigation_allowed
from .office_loader import office_html
from .secure_file_access import AccessDenied, SecureFileAccess, IMAGE_EXTENSIONS, OFFICE_EXTENSIONS


def register_scheme():
    scheme = QWebEngineUrlScheme(b"doc")
    scheme.setSyntax(QWebEngineUrlScheme.Syntax.Host)
    scheme.setFlags(QWebEngineUrlScheme.Flag.SecureScheme)
    QWebEngineUrlScheme.registerScheme(scheme)


class BlockRequests(QWebEngineUrlRequestInterceptor):
    def interceptRequest(self, info):
        url = info.requestUrl()
        if not resource_allowed(url.scheme(), url.host()):
            info.block(True)


class SafePage(QWebEnginePage):
    def acceptNavigationRequest(self, url, nav_type, is_main_frame):
        return navigation_allowed(url.scheme(), url.host())

    def createWindow(self, _type):
        return None


class DocumentSchemeHandler(QWebEngineUrlSchemeHandler):
    def __init__(self, access: SecureFileAccess, parent=None):
        super().__init__(parent)
        self.access = access
        self._buffers = set()

    def requestStarted(self, job):
        url = job.requestUrl()
        if url.host() != "root" or url.query() or url.fragment():
            job.fail(job.Error.UrlInvalid)
            return
        path = unquote(url.path()).lstrip("/")
        # Reject encoded separators/traversal too; SecureFileAccess checks components.
        try:
            kind = os.path.splitext(path)[1].lower()
            if kind == ".md":
                content, mime = markdown_html(self.access, path), b"text/html"
            elif kind in (".html", ".htm"):
                content, mime = html_document(self.access, path), b"text/html"
            elif kind in OFFICE_EXTENSIONS:
                content, mime = office_html(self.access, path), b"text/html"
            elif kind in IMAGE_EXTENSIONS:
                content = self.access.read_asset(path)
                mime = (mimetypes.guess_type(path)[0] or "application/octet-stream").encode()
            else:
                job.fail(job.Error.RequestDenied)
                return
        except (AccessDenied, OSError) as exc:
            content, mime = error_html(str(exc)), b"text/html"
        buffer = QBuffer(job)
        buffer.setData(QByteArray(content))
        buffer.open(QIODevice.OpenModeFlag.ReadOnly)
        self._buffers.add(buffer)
        job.destroyed.connect(lambda _=None, b=buffer: self._buffers.discard(b))
        job.reply(mime, buffer)


class WebViewer(QWebEngineView):
    def __init__(self, access: SecureFileAccess, parent=None):
        super().__init__(parent)
        self.profile = QWebEngineProfile(self)
        self.profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.NoCache)
        self.profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.NoPersistentCookies)
        self.blocker = BlockRequests(self)
        self.profile.setUrlRequestInterceptor(self.blocker)
        self.handler = DocumentSchemeHandler(access, self)
        self.profile.installUrlSchemeHandler(b"doc", self.handler)
        self.page = SafePage(self.profile, self)
        settings = self.page.settings()
        for attribute in (QWebEngineSettings.WebAttribute.JavascriptEnabled,
                          QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls,
                          QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls,
                          QWebEngineSettings.WebAttribute.PluginsEnabled,
                          QWebEngineSettings.WebAttribute.PdfViewerEnabled,
                          QWebEngineSettings.WebAttribute.WebGLEnabled,
                          QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled):
            settings.setAttribute(attribute, False)
        self.setPage(self.page)
        self.profile.downloadRequested.connect(lambda item: item.cancel())

    def show_document(self, path: str):
        from urllib.parse import quote
        self.setUrl(QUrl("doc://root/" + quote(path, safe="/")))
