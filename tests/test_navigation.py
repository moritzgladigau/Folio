import unittest
from app.navigation import Navigation


class NavigationTests(unittest.TestCase):
    def test_history_and_adjacent(self):
        nav = Navigation()
        nav.documents = ["a.md", "b.txt", "c.pdf"]
        nav.visit("a.md")
        self.assertEqual(nav.adjacent(1), "b.txt")
        self.assertEqual(nav.back(), "a.md")
        self.assertEqual(nav.forward(), "b.txt")
        nav.visit("c.pdf")
        self.assertEqual(nav.adjacent(1), "c.pdf")


if __name__ == "__main__":
    unittest.main()
