"""Optional user-provided word list; no corpus data is bundled with the package."""

import fnmatch
import logging
import random
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)


class CorpusUnavailable(Exception):
    pass


class WordCorpus:
    def __init__(
        self, path: str | None, extra_words: Callable[[], list[str] | dict[str, float | None]] | None = None
    ):
        self.path = Path(path).expanduser() if path else None
        self.extra_words = extra_words or (lambda: [])
        self._words: dict[str, float | None] | None = None

    @property
    def available(self) -> bool:
        return bool(self.words())

    def words(self) -> dict[str, float | None]:
        if self._words is not None:
            return self._words
        loaded: dict[str, float | None] = {}
        if self.path is not None and self.path.is_file():
            with self.path.open(encoding="utf-8") as stream:
                for line_number, raw in enumerate(stream, 1):
                    line = raw.strip()
                    if not line or line.startswith("#"):
                        continue
                    fields = line.split("\t", 1)
                    word = fields[0].strip().lower()
                    if not word:
                        continue
                    frequency = None
                    if len(fields) == 2:
                        try:
                            frequency = float(fields[1])
                        except ValueError:
                            logger.warning("Ignoring invalid corpus frequency", extra={"line": line_number})
                    loaded[word] = frequency
        extras = self.extra_words()
        if isinstance(extras, dict):
            loaded.update({word.lower(): frequency for word, frequency in extras.items()})
        else:
            for word in extras:
                loaded.setdefault(word.lower(), None)
        self._words = loaded
        return loaded

    def _require(self) -> dict[str, float | None]:
        values = self.words()
        if not values:
            raise CorpusUnavailable("No offline word corpus is configured")
        return values

    def search(
        self,
        *,
        prefix: str | None = None,
        pattern: str | None = None,
        anagram: str | None = None,
        length: int | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[str]:
        words = self._require()
        results = list(words)
        if prefix is not None:
            results = [word for word in results if word.startswith(prefix.lower())]
        if pattern is not None:
            results = [word for word in results if fnmatch.fnmatchcase(word, pattern.lower())]
        if anagram is not None:
            key = sorted(ch for ch in anagram.lower() if ch.isalpha())
            results = [
                word
                for word in results
                if word != anagram.lower() and sorted(ch for ch in word if ch.isalpha()) == key
            ]
        if length is not None:
            results = [word for word in results if len(word) == length]
        return sorted(results)[offset : offset + limit]

    def random_word(self) -> str:
        return random.choice(list(self._require()))

    def word_of_day(self, iso_date: str) -> str:
        words = sorted(self._require())
        # Stable across machines and process restarts for the same UTC date.
        import hashlib

        index = int(hashlib.sha256(iso_date.encode("utf-8")).hexdigest(), 16) % len(words)
        return words[index]

    def frequency(self, word: str) -> float | None:
        return self._require().get(word.lower())
