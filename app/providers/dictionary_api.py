from urllib.parse import quote

from app.config.settings import settings
from app.providers.http import ProviderError, get_json


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output = []
    for value in values:
        value = value.strip()
        folded = value.casefold()
        if folded and folded not in seen:
            seen.add(folded)
            output.append(value)
    return output


class DictionaryApiProvider:
    name = "dictionaryapi.dev"

    def __init__(self, base_url: str | None = None, timeout: float | None = None, retries: int | None = None):
        self.base_url = (base_url or settings.dictionary_api_url).rstrip("/") + "/"
        self.timeout = timeout if timeout is not None else settings.request_timeout
        self.retries = retries if retries is not None else settings.retry_count

    def lookup(self, word: str) -> dict:
        raw = get_json(
            quote(self.base_url + word, safe=":/"),
            timeout=self.timeout,
            retries=self.retries,
            missing_is_not_found=True,
        )
        if not isinstance(raw, list) or not raw or any(not isinstance(row, dict) for row in raw):
            raise ProviderError("Dictionary provider returned malformed data")

        meanings: list[dict] = []
        phonetics: list[dict] = []
        synonyms: list[str] = []
        antonyms: list[str] = []
        origins: list[str] = []
        for entry in raw:
            origin = entry.get("origin")
            if isinstance(origin, str):
                origins.append(origin)
            for pronunciation in entry.get("phonetics", []):
                if isinstance(pronunciation, dict) and (
                    pronunciation.get("text") or pronunciation.get("audio")
                ):
                    phonetics.append(
                        {"text": pronunciation.get("text"), "audio": pronunciation.get("audio") or None}
                    )
            for meaning in entry.get("meanings", []):
                if not isinstance(meaning, dict):
                    continue
                definitions = []
                for definition in meaning.get("definitions", []):
                    if not isinstance(definition, dict) or not isinstance(definition.get("definition"), str):
                        continue
                    definitions.append(
                        {
                            "definition": definition["definition"],
                            "example": (
                                definition.get("example")
                                if isinstance(definition.get("example"), str)
                                else None
                            ),
                        }
                    )
                    synonyms.extend(x for x in definition.get("synonyms", []) if isinstance(x, str))
                    antonyms.extend(x for x in definition.get("antonyms", []) if isinstance(x, str))
                if definitions:
                    meanings.append(
                        {"part_of_speech": meaning.get("partOfSpeech"), "definitions": definitions}
                    )
                synonyms.extend(x for x in meaning.get("synonyms", []) if isinstance(x, str))
                antonyms.extend(x for x in meaning.get("antonyms", []) if isinstance(x, str))

        return {
            "word": word,
            "meanings": [d["definition"] for m in meanings for d in m["definitions"]],
            "meaning_details": meanings,
            "phonetics": phonetics,
            "synonyms": _unique(synonyms),
            "antonyms": _unique(antonyms),
            "related_words": [],
            "origins": _unique(origins),
            "frequency_per_million": None,
            "sources": [self.name],
        }
