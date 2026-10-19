from unittest.mock import Mock

import pytest
import requests
from fastapi.testclient import TestClient

from app.main import create_app
from app.routes.dictionary import service

client = TestClient(create_app())


@pytest.fixture(autouse=True)
def clear_service_cache():
    service.cache.clear()


def response(status, payload):
    result = Mock()
    result.status_code = status
    result.json.return_value = payload
    if status >= 400:
        result.raise_for_status.side_effect = requests.HTTPError(response=result)
    return result


def mock_providers(
    monkeypatch,
    *,
    dictionary=None,
    synonyms=None,
    antonyms=None,
    rhymes=None,
    suggestions=None,
    search_results=None,
):
    def get(url, params=None, timeout=None):
        assert timeout is not None
        if "dictionaryapi" in url:
            return response(
                200,
                dictionary
                or [
                    {
                        "phonetics": [{"text": "/ˈæp.əl/", "audio": "https://audio.example/apple.mp3"}],
                        "meanings": [
                            {
                                "partOfSpeech": "noun",
                                "definitions": [
                                    {
                                        "definition": "A fruit.",
                                        "example": "I ate an apple.",
                                        "synonyms": ["pome"],
                                    },
                                    {"definition": "A tree producing this fruit."},
                                ],
                            }
                        ],
                    }
                ],
            )
        if "s" in (params or {}):
            return response(200, suggestions or [])
        if "sp" in (params or {}):
            return response(200, search_results or [])
        relation = next(k for k in params if k.startswith("rel_"))
        values = {"rel_syn": synonyms, "rel_ant": antonyms, "rel_rhy": rhymes}.get(relation)
        return response(200, values or [])

    monkeypatch.setattr("app.utils.api_client.requests.get", get)


def test_home():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["api_version"] == "v2"
    assert client.get("/openapi.json").json()["info"]["version"] == "2.0.0"


def test_define_preserves_legacy_fields_and_adds_metadata(monkeypatch):
    mock_providers(monkeypatch, synonyms=[{"word": "orchard apple"}], antonyms=[{"word": "banana"}])
    result = client.get("/define/ APPLE ")
    assert result.status_code == 200
    data = result.json()
    assert data["word"] == "apple"
    assert data["meanings"] == ["A fruit.", "A tree producing this fruit."]
    assert data["synonyms"] == ["pome", "orchard apple"]
    assert data["phonetics"][0]["audio"].endswith("apple.mp3")
    assert data["meaning_details"][0]["definitions"][0]["example"] == "I ate an apple."
    assert data["antonyms"] == ["banana"]


def test_dictionary_404_is_not_found(monkeypatch):
    monkeypatch.setattr("app.utils.api_client.requests.get", lambda *a, **k: response(404, {}))
    result = client.get("/define/asdkfjhasdkjfh")
    assert result.status_code == 404


def test_invalid_word_is_validation_error():
    assert client.get("/define/hello%3Cscript%3E").status_code == 422


def test_datamuse_failure_keeps_dictionary_result(monkeypatch):
    def get(url, params=None, timeout=None):
        if "dictionaryapi" in url:
            return response(
                200, [{"meanings": [{"partOfSpeech": "noun", "definitions": [{"definition": "A test."}]}]}]
            )
        raise requests.Timeout()

    monkeypatch.setattr("app.utils.api_client.requests.get", get)
    assert client.get("/define/test").json()["meanings"] == ["A test."]


def test_dictionary_provider_failure_returns_503(monkeypatch):
    def timeout(*args, **kwargs):
        raise requests.Timeout()

    monkeypatch.setattr("app.utils.api_client.requests.get", timeout)
    assert client.get("/define/test").status_code == 503


def test_missing_optional_fields_and_multiple_entries(monkeypatch):
    mock_providers(
        monkeypatch,
        dictionary=[
            {"meanings": [{"partOfSpeech": "noun", "definitions": [{"definition": "First."}]}]},
            {
                "origin": "From Latin.",
                "meanings": [
                    {
                        "partOfSpeech": "verb",
                        "definitions": [{"definition": "Second.", "example": "A sample."}],
                    }
                ],
            },
        ],
    )
    data = client.get("/define/example").json()
    assert data["meanings"] == ["First.", "Second."]
    assert data["phonetics"] == []
    assert data["origins"] == ["From Latin."]


def test_duplicate_relations_are_removed(monkeypatch):
    mock_providers(
        monkeypatch,
        dictionary=[{"meanings": [{"synonyms": ["Pome"], "definitions": []}]}],
        synonyms=[{"word": "pome"}, {"word": "orchard apple"}],
    )
    assert client.get("/define/apple").json()["synonyms"] == ["Pome", "orchard apple"]


def test_malformed_dictionary_json_returns_503(monkeypatch):
    bad_response = response(200, None)
    bad_response.json.side_effect = ValueError("invalid json")
    monkeypatch.setattr("app.utils.api_client.requests.get", lambda *a, **k: bad_response)
    assert client.get("/define/test").status_code == 503


def test_http_429_and_500_return_predictable_failure(monkeypatch):
    for status in (429, 500):
        calls = 0

        def get(*args, **kwargs):
            nonlocal calls
            calls += 1
            return response(status, {})

        monkeypatch.setattr("app.utils.api_client.requests.get", get)
        assert client.get("/define/test").status_code == 503
        assert calls == 2


def test_connection_failure_is_retried_and_classified(monkeypatch):
    calls = 0

    def get(*args, **kwargs):
        nonlocal calls
        calls += 1
        raise requests.ConnectionError("offline")

    monkeypatch.setattr("app.utils.api_client.requests.get", get)
    assert client.get("/define/test").status_code == 503
    assert calls == 2


def test_datamuse_404_is_partial_failure_not_missing_word(monkeypatch):
    def get(url, params=None, timeout=None):
        if "dictionaryapi" in url:
            return response(200, [{"meanings": [{"definitions": [{"definition": "A test."}]}]}])
        return response(404, {})

    monkeypatch.setattr("app.utils.api_client.requests.get", get)
    result = client.get("/define/test")
    assert result.status_code == 200
    assert result.json()["meanings"] == ["A test."]
    assert result.json()["sources"] == ["dictionaryapi.dev"]


def test_versioned_routes_and_relationship_endpoints(monkeypatch):
    mock_providers(
        monkeypatch,
        synonyms=[{"word": "glad"}],
        antonyms=[{"word": "sad"}],
        rhymes=[{"word": "time"}],
        suggestions=[{"word": "hello"}],
    )
    assert client.get("/api/v2/define/happy").status_code == 200
    assert client.get("/api/v2/synonyms/happy").json()["synonyms"] == ["pome", "glad"]
    assert client.get("/api/v2/antonyms/happy").json()["antonyms"] == ["sad"]
    assert client.get("/api/v2/rhymes/rhyme").json()["rhymes"] == ["time"]
    assert client.get("/api/v2/suggest/helo").json()["suggestions"] == ["hello"]


def test_phrase_and_url_encoded_input(monkeypatch):
    mock_providers(monkeypatch)
    result = client.get("/api/v2/define/ice%20cream")
    assert result.status_code == 200
    assert result.json()["word"] == "ice cream"


def test_batch_has_per_word_outcomes_and_accepts_duplicates(monkeypatch):
    mock_providers(monkeypatch)
    result = client.post("/api/v2/define/batch", json={"words": ["apple", "apple", "bad<script>"]})
    assert result.status_code == 200
    rows = result.json()["results"]
    assert [row["ok"] for row in rows] == [True, True, False]
    assert rows[0]["entry"]["word"] == rows[1]["entry"]["word"] == "apple"


def test_batch_size_limit(monkeypatch):
    result = client.post("/api/v2/define/batch", json={"words": ["x"] * 51})
    assert result.status_code == 413


def test_health_distinguishes_unchecked_from_probed(monkeypatch):
    result = client.get("/api/v2/health").json()
    assert result["application"] == "ok"
    assert result["providers"] == {"dictionary": "not_checked", "datamuse": "not_checked"}
    mock_providers(monkeypatch)
    result = client.get("/api/v2/health?check_providers=true").json()
    assert result["providers"] == {"dictionary": "healthy", "datamuse": "healthy"}


def test_prefix_search_uses_datamuse_and_paginates(monkeypatch):
    mock_providers(monkeypatch, search_results=[{"word": "prelude"}, {"word": "prefix"}, {"word": "presto"}])
    result = client.get("/api/v2/search?prefix=pre&limit=1&offset=1")
    assert result.status_code == 200
    assert result.json()["results"] == ["prefix"]


def test_context_reorders_definitions_without_changing_them(monkeypatch):
    mock_providers(
        monkeypatch,
        dictionary=[
            {
                "meanings": [
                    {"partOfSpeech": "noun", "definitions": [{"definition": "A round fruit."}]},
                    {"partOfSpeech": "noun", "definitions": [{"definition": "A company making computers."}]},
                ]
            }
        ],
    )
    result = client.get("/api/v2/define/apple?context=company%20computers")
    assert result.status_code == 200
    data = result.json()
    assert data["meanings"][0] == "A company making computers."
    assert data["ranking"] == "context-token-overlap"


def test_relationship_graph_is_bounded_and_attributed(monkeypatch):
    mock_providers(monkeypatch, synonyms=[{"word": "glad"}, {"word": "joyful"}])
    result = client.get("/api/v2/graph/happy?depth=1&limit=2")
    assert result.status_code == 200
    data = result.json()
    assert data["root"] == "happy"
    assert len(data["nodes"]) <= 2
    assert data["edges"][0]["relation"] == "syn"
    assert data["sources"] == ["datamuse"]
