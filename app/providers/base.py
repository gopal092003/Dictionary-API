from typing import Protocol


class DictionaryProvider(Protocol):
    name: str

    def lookup(self, word: str) -> dict: ...


class RelationshipProvider(Protocol):
    name: str

    def relation(self, word: str, relation: str, limit: int = 100) -> list[str]: ...

    def suggest(self, word: str, limit: int = 10) -> list[str]: ...

    def search(
        self, *, prefix: str | None = None, pattern: str | None = None, limit: int = 20, offset: int = 0
    ) -> list[str]: ...
