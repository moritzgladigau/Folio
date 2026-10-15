import io
import pathlib
import tempfile
import unittest
import zipfile

from app.document_loader import CSP, rtf_text
from app.office_loader import office_html
from app.secure_file_access import AccessDenied, SecureFileAccess


def archive(member, content):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as package:
        package.writestr(member, content)
    return output.getvalue()


class ExtraFormatTests(unittest.TestCase):
    def test_rtf_and_visible_formats(self):
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            (root / "note.rtf").write_bytes(b"{\\rtf1\\ansi Hello \\b world\\b0!}")
            for name in ("data.json", "photo.png", "scan.jpeg", "draft.docx", "letter.odt"):
                (root / name).write_bytes(b"test")
            with SecureFileAccess(folder) as access:
                self.assertIn("Hello world!", rtf_text(access, "note.rtf"))
                self.assertEqual({e.path for e in access.list_dir()}, {"note.rtf", "data.json", "photo.png", "scan.jpeg", "draft.docx", "letter.odt"})

    def test_office_preview_escapes_content_and_blocks_external_xml(self):
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            docx = b'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>&lt;script&gt;bad&lt;/script&gt;</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>Cell</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:body></w:document>'
            odt = b'<office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"><office:body><office:text><text:p>Hallo &amp; Welt</text:p></office:text></office:body></office:document-content>'
            (root / "draft.docx").write_bytes(archive("word/document.xml", docx))
            (root / "letter.odt").write_bytes(archive("content.xml", odt))
            with SecureFileAccess(folder) as access:
                docx_page = office_html(access, "draft.docx")
                odt_page = office_html(access, "letter.odt")
            self.assertIn(CSP.encode(), docx_page)
            self.assertIn(b"&lt;script&gt;bad&lt;/script&gt;", docx_page)
            self.assertNotIn(b"<script>bad</script>", docx_page)
            self.assertIn(b"<table>", docx_page)
            self.assertIn(b"Hallo &amp; Welt", odt_page)

            malicious = b'<!DOCTYPE x [<!ENTITY secret SYSTEM "file:///etc/passwd">]><x>&secret;</x>'
            (root / "evil.odt").write_bytes(archive("content.xml", malicious))
            with SecureFileAccess(folder) as access:
                with self.assertRaises(AccessDenied):
                    office_html(access, "evil.odt")

    def test_corrupt_and_oversized_office_member(self):
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            (root / "bad.docx").write_bytes(b"not a zip")
            (root / "large.odt").write_bytes(archive("content.xml", b"a" * (16 * 1024 * 1024 + 1)))
            with SecureFileAccess(folder) as access:
                for path in ("bad.docx", "large.odt"):
                    with self.assertRaises(AccessDenied):
                        office_html(access, path)


if __name__ == "__main__":
    unittest.main()
