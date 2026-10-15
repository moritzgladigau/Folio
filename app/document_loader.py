"""Document rendering data; every source read goes through SecureFileAccess."""
import html
import os

import markdown
from pygments.formatters import HtmlFormatter
from striprtf.striprtf import rtf_to_text

from .secure_file_access import SecureFileAccess

STYLE = """<style>
:root{color-scheme:light dark}body{font:16px/1.65 system-ui,sans-serif;max-width:860px;margin:48px auto;padding:0 32px;color:#243044;background:#fff}
@media(prefers-color-scheme:dark){body{color:#e5e9f0;background:#20242b}a{color:#8ec7ff}pre,code{background:#303640}}
h1,h2,h3{line-height:1.25}h1{font-size:2.1em}h2{border-bottom:1px solid #8993a344;padding-bottom:.25em}
pre{padding:18px;overflow:auto;border-radius:8px;background:#f2f4f7}code{font-family:ui-monospace,monospace}
table{border-collapse:collapse;width:100%}td,th{border:1px solid #8993a355;padding:8px 12px}img{max-width:100%}
blockquote{border-left:4px solid #748ca5;padding-left:20px;color:#77828f}
"""
STYLE += HtmlFormatter().get_style_defs(".codehilite")

CSP = "<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; img-src doc: data:; style-src 'unsafe-inline'; font-src 'none'; script-src 'none'; connect-src 'none'; frame-src 'none'; object-src 'none'; form-action 'none'; base-uri 'none'\">"


def markdown_html(access: SecureFileAccess, path: str) -> bytes:
    source = access.read_text(path)
    body = markdown.markdown(source, extensions=["tables", "fenced_code", "codehilite", "sane_lists"])
    return ("<!doctype html><html><head><meta charset=utf-8>" + CSP + STYLE + "</style></head><body>" + body + "</body></html>").encode("utf-8")


def html_document(access: SecureFileAccess, path: str) -> bytes:
    source = access.read_text(path)
    # A prepended CSP applies even to malformed or full HTML documents.
    return ("<!doctype html><head><meta charset=utf-8>" + CSP + STYLE + "</style></head>" + source).encode("utf-8")


def rtf_text(access: SecureFileAccess, path: str) -> str:
    source = access.read_bytes(path, limit=16 * 1024 * 1024)
    return rtf_to_text(source.decode("latin-1"), errors="replace")


def error_html(message: str) -> bytes:
    return ("<!doctype html><html><head><meta charset=utf-8>" + STYLE + "</style></head><body><h2>Dokument nicht verfügbar</h2><p>" + html.escape(message) + "</p></body></html>").encode()


def document_kind(path: str) -> str:
    return os.path.splitext(path)[1].lower()


def resource_allowed(scheme: str, host: str) -> bool:
    return (scheme == "doc" and host == "root") or scheme == "data"


def navigation_allowed(scheme: str, host: str) -> bool:
    return scheme == "doc" and host == "root"
