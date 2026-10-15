"""Small, bounded text preview of DOCX and ODT files, without external resources."""
from __future__ import annotations

import html
import io
import re
import zipfile

from defusedxml import ElementTree
from defusedxml.common import DefusedXmlException

from .document_loader import CSP, STYLE
from .secure_file_access import AccessDenied, SecureFileAccess

MAX_ARCHIVE = 64 * 1024 * 1024
MAX_XML = 16 * 1024 * 1024
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
O = "{urn:oasis:names:tc:opendocument:xmlns:office:1.0}"
T = "{urn:oasis:names:tc:opendocument:xmlns:text:1.0}"
TABLE = "{urn:oasis:names:tc:opendocument:xmlns:table:1.0}"


def _package_xml(data: bytes, member: str):
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            info = archive.getinfo(member)
            if info.file_size > MAX_XML:
                raise AccessDenied("Office-Dokument ist zu groß")
            with archive.open(info) as source:
                xml = source.read(MAX_XML + 1)
            if len(xml) > MAX_XML:
                raise AccessDenied("Office-Dokument ist zu groß")
        return ElementTree.fromstring(xml)
    except (zipfile.BadZipFile, KeyError, RuntimeError, ElementTree.ParseError, DefusedXmlException, OSError) as exc:
        raise AccessDenied("Office-Dokument ist beschädigt oder nicht lesbar") from exc


def _docx_text(node):
    result = []
    for part in node.iter():
        if part.tag == W + "t":
            result.append(part.text or "")
        elif part.tag == W + "tab":
            result.append("\t")
        elif part.tag in (W + "br", W + "cr"):
            result.append("\n")
    return "".join(result)


def _docx_blocks(node):
    blocks = []
    for child in node:
        if child.tag == W + "p":
            value = _docx_text(child)
            if not value.strip():
                continue
            style = child.find(f"{W}pPr/{W}pStyle")
            heading = re.fullmatch(r"Heading([1-6])", style.get(W + "val", "")) if style is not None else None
            tag = "h" + heading.group(1) if heading else "p"
            blocks.append(f"<{tag}>{html.escape(value).replace(chr(10), '<br>')}</{tag}>")
        elif child.tag == W + "tbl":
            rows = []
            for row in child.findall(W + "tr"):
                cells = [f"<td>{html.escape(_docx_text(cell))}</td>" for cell in row.findall(W + "tc")]
                rows.append("<tr>" + "".join(cells) + "</tr>")
            blocks.append("<table>" + "".join(rows) + "</table>")
    return blocks


def _odt_text(node):
    return "".join(node.itertext())


def _odt_blocks(node):
    blocks = []
    for child in node:
        if child.tag in (T + "p", T + "h"):
            value = _odt_text(child)
            if value.strip():
                level = child.get(T + "outline-level", "2")
                tag = "h" + level if child.tag == T + "h" and level in "123456" else "p"
                blocks.append(f"<{tag}>{html.escape(value)}</{tag}>")
        elif child.tag == T + "list":
            blocks.append("<ul>" + "".join("<li>" + html.escape(" ".join(_odt_text(p) for p in item.iter() if p.tag in (T + "p", T + "h"))) + "</li>" for item in child if item.tag == T + "list-item") + "</ul>")
        elif child.tag == TABLE + "table":
            rows = []
            for row in child.findall(TABLE + "table-row"):
                cells = [f"<td>{html.escape(_odt_text(cell))}</td>" for cell in row.findall(TABLE + "table-cell")]
                rows.append("<tr>" + "".join(cells) + "</tr>")
            blocks.append("<table>" + "".join(rows) + "</table>")
    return blocks


def office_html(access: SecureFileAccess, path: str) -> bytes:
    if path.lower().endswith(".docx"):
        root = _package_xml(access.read_bytes(path, MAX_ARCHIVE), "word/document.xml")
        body = root.find(W + "body")
        blocks = _docx_blocks(body) if body is not None else []
    elif path.lower().endswith(".odt"):
        root = _package_xml(access.read_bytes(path, MAX_ARCHIVE), "content.xml")
        body = root.find(f"{O}body/{O}text")
        blocks = _odt_blocks(body) if body is not None else []
    else:
        raise AccessDenied("Office-Format nicht unterstützt")
    page = "<!doctype html><html><head><meta charset=utf-8>" + CSP + STYLE + "</style></head><body>" + "".join(blocks) + "</body></html>"
    return page.encode("utf-8")
