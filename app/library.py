"""Reusable Python API for local applications and scripts."""

from app.config.settings import Settings, settings
from app.services.dictionary_service import DictionaryService, create_default_service
from app.vocabulary import VocabularyStore

__all__ = ["DictionaryClient", "VocabularyStore"]


class DictionaryClient:
    def __init__(self, service: DictionaryService | None = None, config: Settings = settings):
        self.service = service or create_default_service(config)
        self.max_batch_size = config.max_batch_size

    def define(self, word: str, context: str | None = None) -> dict:
        return self.service.define(word, context)

    def synonyms(self, word: str, limit: int = 100) -> dict:
        return self.service.synonyms(word, limit)

    def antonyms(self, word: str, limit: int = 100) -> dict:
        return self.service.antonyms(word, limit)

    def related(self, word: str, kind: str = "associations", limit: int = 20) -> dict:
        return self.service.related(word, kind, limit)

    def relationship_graph(self, word: str, depth: int = 1, limit: int = 50) -> dict:
        return self.service.relationship_graph(word, depth, limit)

    def rhymes(self, word: str, limit: int = 20) -> dict:
        return self.service.rhymes(word, limit)

    def suggest(self, word: str, limit: int = 10) -> dict:
        return self.service.suggest(word, limit)

    def search(self, **kwargs) -> dict:
        return self.service.search(**kwargs)

    def forms(self, word: str, part_of_speech: str | None = None) -> dict:
        return self.service.forms(word, part_of_speech)

    def frequency(self, word: str) -> dict:
        return self.service.frequency(word)

    def random_word(self) -> dict:
        return self.service.random_word()

    def word_of_day(self) -> dict:
        return self.service.word_of_day()

    def clear_cache(self) -> None:
        self.service.cache.clear()

    def define_batch(self, words: list[str]) -> list[dict]:
        if not words:
            raise ValueError("Provide at least one word")
        if len(words) > self.max_batch_size:
            raise ValueError(f"Batch size cannot exceed {self.max_batch_size}")
        results = []
        for word in words:
            try:
                results.append({"word": word, "ok": True, "entry": self.define(word), "error": None})
            except Exception as exc:
                results.append({"word": word, "ok": False, "entry": None, "error": str(exc)})
        return results
