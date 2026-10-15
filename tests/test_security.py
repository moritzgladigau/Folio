import os
import pathlib
import tempfile
import unittest

from app.secure_file_access import AccessDenied, SecureFileAccess


class SecurityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name) / "root"
        self.root.mkdir()
        (self.root / "inside.txt").write_text("hello", encoding="utf-8")
        (pathlib.Path(self.tmp.name) / "outside.txt").write_text("secret")
        self.access = SecureFileAccess(str(self.root))

    def tearDown(self):
        self.access.close()
        self.tmp.cleanup()

    def test_inside_and_path_traversal(self):
        self.assertEqual(self.access.read_text("inside.txt"), "hello")
        for path in ("../outside.txt", "/etc/passwd", "sub/../inside.txt", "./inside.txt"):
            with self.assertRaises(AccessDenied):
                self.access.read_bytes(path)

    def test_symlinks_inside_and_outside(self):
        (self.root / "outside.txt").symlink_to(pathlib.Path(self.tmp.name) / "outside.txt")
        (self.root / "inside-link.txt").symlink_to(self.root / "inside.txt")
        for path in ("outside.txt", "inside-link.txt"):
            with self.assertRaises(AccessDenied):
                self.access.read_bytes(path)
        self.assertEqual([e.path for e in self.access.list_dir()], ["inside.txt"])

    def test_symlink_swap(self):
        (self.root / "inside.txt").unlink()
        (self.root / "inside.txt").symlink_to(pathlib.Path(self.tmp.name) / "outside.txt")
        with self.assertRaises(AccessDenied):
            self.access.read_text("inside.txt")

    def test_symlink_directory(self):
        (self.root / "linked").symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(AccessDenied):
            self.access.read_text("linked/inside.txt")

    def test_read_only_api_and_unchanged_directory(self):
        before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.iterdir()}
        self.access.read_text("inside.txt")
        self.assertFalse(hasattr(self.access, "write_bytes"))
        self.assertFalse(hasattr(self.access, "delete"))
        with self.assertRaises(AttributeError):
            self.access.root = "/"
        after = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.iterdir()}
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
