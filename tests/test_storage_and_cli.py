import json
import time

from app.cache import MemoryCache, SQLiteCache
from app.cli import main
from app.providers.http import ProviderError, WordNotFound
from app.providers.offline_dictionary import OfflineDictionaryProvider
from app.services.dictionary_service import DictionaryService
from app.vocabulary import VocabularyStore


class CountingDictionary:
    name = "counting"

    def __init__(self, fail=False):
        self.calls = 0
        self.fail = fail

    def lookup(self, word):
        self.calls += 1
        if self.fail:
            raise ProviderError("offline")
        return {
            "word": word,
            "meanings": ["A test."],
            "meaning_details": [],
            "phonetics": [],
            "synonyms": [],
            "antonyms": [],
            "related_words": [],
            "origins": [],
            "frequency_per_million": None,
            "sources": [self.name],
        }


class EmptyRelations:
    name = "relations"

    def __init__(self):
        self.calls = 0

    def relation(self, word, relation, limit=100):
        self.calls += 1
        return []

    def suggest(self, word, limit=10):
        return []

    def search(self, **kwargs):
        return []


def test_memory_cache_hit_expiry_and_clear():
    cache = MemoryCache()
    cache.set("key", {"value": 1}, 30)
    assert cache.get("key") == {"value": 1}
    cache.set("expired", True, 0)
    assert cache.get("expired") is None
    cache.set("short-lived", "value", 1)
    time.sleep(1.01)
    assert cache.get("short-lived") is None
    cache.clear()
    assert cache.get("key") is None


def test_sqlite_cache_persists_expires_and_clears(tmp_path):
    path = str(tmp_path / "cache.sqlite3")
    first = SQLiteCache(path)
    first.set("persist", [1, 2], 30)
    assert SQLiteCache(path).get("persist") == [1, 2]
    first.set("expired", "old", 0)
    assert first.get("expired") is None
    first.clear()
    assert first.get("persist") is None


def test_service_caches_successful_provider_results():
    dictionary = CountingDictionary()
    relationships = EmptyRelations()
    service = DictionaryService(
        dictionary_provider=dictionary,
        relationship_provider=relationships,
        offline_provider=OfflineDictionaryProvider(None),
        cache=MemoryCache(),
    )
    service.define("example")
    service.define("example")
    assert dictionary.calls == 1
    assert relationships.calls == 3


def test_failed_provider_response_is_not_cached():
    dictionary = CountingDictionary(fail=True)
    service = DictionaryService(
        dictionary_provider=dictionary,
        relationship_provider=EmptyRelations(),
        offline_provider=OfflineDictionaryProvider(None),
        cache=MemoryCache(),
    )
    for _ in range(2):
        try:
            service.define("example")
        except ProviderError:
            pass
        else:
            raise AssertionError("provider failure should propagate")
    assert dictionary.calls == 2


def test_vocabulary_crud_json_csv_import_export(tmp_path):
    store = VocabularyStore(str(tmp_path / "vocab.sqlite3"))
    store.add("study", "Apple", {"meanings": ["fruit"]})
    store.add("study", "apple")
    store.add("study", "banana")
    assert [item["word"] for item in store.list_words("study")] == ["apple", "banana"]
    assert store.list_names() == ["study"]
    assert store.remove("study", "banana") is True
    assert store.remove("study", "missing") is False

    json_path = tmp_path / "study.json"
    store.export_file(str(json_path), "study")
    imported = VocabularyStore(str(tmp_path / "imported.sqlite3"))
    assert imported.import_file(str(json_path), "saved") == 1
    assert imported.list_words("saved")[0]["entry"] == {"meanings": ["fruit"]}

    csv_path = tmp_path / "study.csv"
    store.export_file(str(csv_path), "study")
    assert imported.import_file(str(csv_path), "csv") == 1
    assert imported.list_words("csv")[0]["word"] == "apple"


def test_flashcard_export_uses_saved_definitions_only(tmp_path):
    store = VocabularyStore(str(tmp_path / "cards.sqlite3"))
    store.add("study", "apple", {"meanings": ["A fruit."], "sources": ["offline"]})
    store.add("study", "unknown")
    output = tmp_path / "cards.json"
    count, skipped = store.export_flashcards_file(str(output), "study")
    cards = json.loads(output.read_text(encoding="utf-8"))
    assert count == 1 and skipped == 1
    assert cards == [{"front": "apple", "back": "A fruit.", "sources": "offline"}]


def test_cli_success_and_unknown_word_exit_codes(monkeypatch, capsys):
    class GoodClient:
        def define(self, word, context=None):
            return {"word": word}

    monkeypatch.setattr("app.cli.DictionaryClient", GoodClient)
    assert main(["define", "apple"]) == 0
    assert json.loads(capsys.readouterr().out) == {"word": "apple"}

    class MissingClient:
        def define(self, word, context=None):
            raise WordNotFound("unknown")

    monkeypatch.setattr("app.cli.DictionaryClient", MissingClient)
    assert main(["define", "unknown"]) == 2
    assert "unknown" in capsys.readouterr().err

    class UnavailableClient:
        def define(self, word, context=None):
            raise ProviderError("network down")

    monkeypatch.setattr("app.cli.DictionaryClient", UnavailableClient)
    assert main(["define", "apple"]) == 3
    assert "Provider unavailable" in capsys.readouterr().err


def test_cli_batch_returns_all_results_and_partial_failure_exit_code(monkeypatch, capsys):
    class BatchClient:
        def define_batch(self, words):
            return [
                {"word": word, "ok": word != "missing", "entry": {"word": word}, "error": None}
                for word in words
            ]

    monkeypatch.setattr("app.cli.DictionaryClient", BatchClient)
    assert main(["batch", "apple", "missing"]) == 4
    output = json.loads(capsys.readouterr().out)
    assert [item["word"] for item in output] == ["apple", "missing"]
    assert [item["ok"] for item in output] == [True, False]
