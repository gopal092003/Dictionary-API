"""Adapter for an optional, user-supplied JSON Lines dictionary file."""

import json
import logging
from pathlib import Path
from threading import Lock

from app.providers.http import WordNotFound

logger = logging.getLogger(__name__)


class OfflineDictionaryProvider:
    name = "offline-dictionary"

    def __init__(self, path: str | None):
        self.path = Path(path).expanduser() if path else None
        self._entries: dict[str, dict] | None = None
        self._lock = Lock()

    @property
    def available(self) -> bool:
        return self.path is not None and self.path.is_file()

    def _load(self) -> dict[str, dict]:
        if self._entries is not None:
            return self._entries
        with self._lock:
            if self._entries is not None:
                return self._entries
            rows: dict[str, dict] = {}
            path = self.path
            if path is not None and path.is_file():
                with path.open(encoding="utf-8") as stream:
                    for line_number, line in enumerate(stream, 1):
                        try:
                            row = json.loads(line)
                            if not isinstance(row, dict):
                                continue
                            word = str(row["word"]).strip().lower()
                            if not word:
                                continue
                            meanings = row.get("meaning_details", row.get("meanings", []))
                            if meanings and isinstance(meanings[0], str):
                                meanings = [
                                    {
                                        "part_of_speech": None,
                                        "definitions": [
                                            {"definition": value, "example": None} for value in meanings
                                        ],
                                    }
                                ]
                            normalized_meanings: list[dict] = []
                            for meaning in meanings if isinstance(meanings, list) else []:
                                if not isinstance(meaning, dict):
                                    continue
                                defs = []
                                for definition in meaning.get("definitions", []):
                                    if isinstance(definition, str):
                                        defs.append({"definition": definition, "example": None})
                                    elif isinstance(definition, dict) and isinstance(
                                        definition.get("definition"), str
                                    ):
                                        defs.append(
                                            {
                                                "definition": definition["definition"],
                                                "example": definition.get("example"),
                                            }
                                        )
                                if defs:
                                    normalized_meanings.append(
                                        {"part_of_speech": meaning.get("part_of_speech"), "definitions": defs}
                                    )
                            flat = [d["definition"] for m in normalized_meanings for d in m["definitions"]]
                            frequency = row.get("frequency_per_million")
                            if not isinstance(frequency, (int, float)) or isinstance(frequency, bool):
                                frequency = None

                            def string_list(key: str) -> list[str]:
                                value = row.get(key, [])
                                if not isinstance(value, list):
                                    return []
                                return [item for item in value if isinstance(item, str)]

                            rows[word] = {
                                "word": word,
                                "meanings": flat,
                                "meaning_details": normalized_meanings,
                                "phonetics": (
                                    [value for value in row.get("phonetics", []) if isinstance(value, dict)]
                                    if isinstance(row.get("phonetics", []), list)
                                    else []
                                ),
                                "synonyms": string_list("synonyms"),
                                "antonyms": string_list("antonyms"),
                                "related_words": string_list("related_words"),
                                "origins": string_list("origins"),
                                "frequency_per_million": frequency,
                                "sources": [self.name],
                            }
                        except (ValueError, TypeError, KeyError) as exc:
                            logger.warning(
                                "Skipping invalid offline dictionary row",
                                extra={"line": line_number, "error_type": type(exc).__name__},
                            )
            self._entries = rows
        return self._entries

    def lookup(self, word: str) -> dict:
        entry = self._load().get(word.lower())
        if entry is None:
            raise WordNotFound
        return entry.copy()

    def words(self) -> list[str]:
        return list(self._load())

    def frequencies(self) -> dict[str, float | None]:
        return {word: entry.get("frequency_per_million") for word, entry in self._load().items()}
