import pathlib
import tempfile
import unittest

from app.document_loader import CSP, html_document, markdown_html, navigation_allowed, resource_allowed
from app.secure_file_access import SecureFileAccess


class DocumentLoaderTests(unittest.TestCase):
    def test_html_and_markdown_guarded(self):
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            (root / "x.html").write_text('<script>alert(1)</script><img src="https://example.org/a.png"><img src="file:///etc/passwd">')
            (root / "x.md").write_text('![external](https://example.org/a.png)\n\n![inside](image.png)')
            with SecureFileAccess(folder) as access:
                self.assertIn(CSP.encode(), html_document(access, "x.html"))
                self.assertIn(CSP.encode(), markdown_html(access, "x.md"))
            for scheme, host in (("https", "example.org"), ("http", "example.org"), ("file", ""), ("ftp", "example.org")):
                self.assertFalse(resource_allowed(scheme, host))
                self.assertFalse(navigation_allowed(scheme, host))
            self.assertTrue(resource_allowed("doc", "root"))
            self.assertFalse(resource_allowed("doc", "evil"))


if __name__ == "__main__":
    unittest.main()
