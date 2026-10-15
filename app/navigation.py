"""Pure navigation state, independent of Qt."""
class Navigation:
    def __init__(self):
        self.documents: list[str] = []
        self.history: list[str] = []
        self.position = -1

    @property
    def current(self):
        return self.history[self.position] if self.position >= 0 else None

    def visit(self, path: str):
        if path not in self.documents or path == self.current:
            return self.current
        self.history = self.history[: self.position + 1] + [path]
        self.position += 1
        return path

    def back(self):
        if self.position > 0:
            self.position -= 1
        return self.current

    def forward(self):
        if self.position + 1 < len(self.history):
            self.position += 1
        return self.current

    def adjacent(self, delta: int):
        if self.current in self.documents:
            i = self.documents.index(self.current) + delta
            if 0 <= i < len(self.documents):
                return self.visit(self.documents[i])
        return self.current
