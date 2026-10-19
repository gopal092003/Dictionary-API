import json

import pytest
from fastapi.testclient import TestClient

from app.cache import MemoryCache, NoCache
from app.local_data import WordCorpus
from app.main import create_app
from app.providers.http import ProviderError
from app.providers.offline_dictionary import OfflineDictionaryProvider
from app.routes import dictionary as route_module
from app.services.dictionary_service import DictionaryService


class OfflineOnlyProvider:
    name = "offline-test"

    def lookup(self, word):
        raise ProviderError("offline test provider")


class EmptyRelations:
    name = "mock-relations"

    def relation(self, word, relation, limit=100):
        return []

    def suggest(self, word, limit=10):
        return []

    def search(self, **kwargs):
        return []


@pytest.fixture
def corpus_client(tmp_path, monkeypatch):
    corpus_path = tmp_path / "words.tsv"
    corpus_path.write_text("act\ncat\nape\napple\napples\ndog\t2.5\n", encoding="utf-8")
    local_service = DictionaryService(
        dictionary_provider=OfflineOnlyProvider(),
        relationship_provider=EmptyRelations(),
        offline_provider=OfflineDictionaryProvider(None),
        cache=MemoryCache(),
        corpus=WordCorpus(str(corpus_path)),
    )
    monkeypatch.setattr(route_module, "service", local_service)
    return TestClient(create_app())


def test_local_search_modes_and_pagination(corpus_client):
    assert corpus_client.get("/api/v2/search?prefix=ap").json()["results"] == ["ape", "apple", "apples"]
    assert corpus_client.get("/api/v2/search?pattern=a%2A&limit=1").json()["results"] == ["act"]
    assert corpus_client.get("/api/v2/search?anagram=act").json()["results"] == ["cat"]
    assert corpus_client.get("/api/v2/search?length=3&offset=1&limit=2").json()["results"] == ["ape", "cat"]
    assert corpus_client.get("/api/v2/search?prefix=z").json()["results"] == []


def test_search_rejects_invalid_or_ambiguous_patterns(corpus_client):
    assert corpus_client.get("/api/v2/search?pattern=%5Babc%5D").status_code == 422
    assert corpus_client.get("/api/v2/search?prefix=a&length=3").status_code == 422


def test_forms_frequency_random_and_deterministic_word(corpus_client):
    running = corpus_client.get("/api/v2/forms/running?part_of_speech=verb").json()
    assert running["lemma"] == "run"
    assert {"ran", "running", "runs"}.issubset(running["forms"])
    children = corpus_client.get("/api/v2/forms/child?part_of_speech=noun").json()
    assert "children" in children["forms"]
    assert corpus_client.get("/api/v2/frequency/dog").json()["frequency_per_million"] == 2.5
    assert corpus_client.get("/api/v2/frequency/cat").json()["frequency_per_million"] is None
    assert corpus_client.get("/api/v2/random").status_code == 200
    first = corpus_client.get("/api/v2/word-of-the-day").json()
    second = corpus_client.get("/api/v2/word-of-the-day").json()
    assert first == second


def test_suggestions_fall_back_to_local_edit_distance(tmp_path):
    path = tmp_path / "words.txt"
    path.write_text("apple\napples\napply\nbanana\n", encoding="utf-8")
    service = DictionaryService(
        dictionary_provider=OfflineOnlyProvider(),
        relationship_provider=EmptyRelations(),
        offline_provider=OfflineDictionaryProvider(None),
        cache=MemoryCache(),
        corpus=WordCorpus(str(path)),
    )
    result = service.suggest("appl", 3)
    assert result["sources"] == ["local-corpus"]
    assert "apple" in result["suggestions"]


def test_local_random_requires_a_corpus(monkeypatch):
    local_service = DictionaryService(
        dictionary_provider=OfflineOnlyProvider(),
        relationship_provider=EmptyRelations(),
        offline_provider=OfflineDictionaryProvider(None),
        cache=NoCache(),
        corpus=WordCorpus(None),
    )
    monkeypatch.setattr(route_module, "service", local_service)
    response = TestClient(create_app()).get("/api/v2/random")
    assert response.status_code == 503


def test_offline_dictionary_fallback_and_frequency(tmp_path, monkeypatch):
    path = tmp_path / "dictionary.jsonl"
    path.write_text(
        json.dumps(
            {
                "word": "quokka",
                "meanings": [
                    {
                        "part_of_speech": "noun",
                        "definitions": [{"definition": "A small marsupial.", "example": "A quokka smiled."}],
                    }
                ],
                "frequency_per_million": 0.4,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    offline = OfflineDictionaryProvider(str(path))
    local_service = DictionaryService(
        dictionary_provider=OfflineOnlyProvider(),
        relationship_provider=EmptyRelations(),
        offline_provider=offline,
        cache=NoCache(),
        corpus=WordCorpus(None, offline.frequencies),
    )
    monkeypatch.setattr(route_module, "service", local_service)
    client = TestClient(create_app())
    entry = client.get("/api/v2/define/quokka")
    assert entry.status_code == 200
    assert entry.json()["meanings"] == ["A small marsupial."]
    assert entry.json()["sources"][0] == "offline-dictionary"
    assert client.get("/api/v2/frequency/quokka").json()["frequency_per_million"] == 0.4
