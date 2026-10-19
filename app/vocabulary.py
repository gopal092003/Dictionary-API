"""SQLite storage for named personal vocabulary lists."""

import csv
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from app.services.dictionary_service import normalize_word


class VocabularyStore:
    def __init__(self, path: str = "dictionary-vocabulary.sqlite3"):
        self.path = str(Path(path).expanduser())
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS vocabulary ("
                "list_name TEXT NOT NULL, word TEXT NOT NULL, "
                "saved_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, "
                "entry_json TEXT, PRIMARY KEY(list_name, word))"
            )

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.path, timeout=5)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def add(self, list_name: str, word: str, entry: dict | None = None) -> None:
        self._validate_list(list_name)
        normalized = normalize_word(word)
        encoded = json.dumps(entry, ensure_ascii=False) if entry is not None else None
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO vocabulary(list_name, word, entry_json) VALUES(?, ?, ?) "
                "ON CONFLICT(list_name, word) DO UPDATE SET "
                "entry_json=COALESCE(excluded.entry_json, entry_json)",
                (list_name, normalized, encoded),
            )

    def remove(self, list_name: str, word: str) -> bool:
        self._validate_list(list_name)
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM vocabulary WHERE list_name = ? AND word = ?", (list_name, normalize_word(word))
            )
            return cursor.rowcount > 0

    def list_words(self, list_name: str = "default") -> list[dict[str, Any]]:
        self._validate_list(list_name)
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT word, saved_at, entry_json FROM vocabulary WHERE list_name = ? ORDER BY word",
                (list_name,),
            ).fetchall()
        return [
            {"word": word, "saved_at": saved_at, "entry": json.loads(entry_json) if entry_json else None}
            for word, saved_at, entry_json in rows
        ]

    def list_names(self) -> list[str]:
        with self._connect() as connection:
            return [
                row[0]
                for row in connection.execute("SELECT DISTINCT list_name FROM vocabulary ORDER BY list_name")
            ]

    def export_file(self, path: str, list_name: str = "default", format: str | None = None) -> None:
        rows = self.list_words(list_name)
        target = Path(path).expanduser()
        kind = (format or target.suffix.lstrip(".")).lower()
        target.parent.mkdir(parents=True, exist_ok=True)
        if kind == "json":
            target.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        elif kind == "csv":
            with target.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=["word", "saved_at", "entry"])
                writer.writeheader()
                for row in rows:
                    writer.writerow(
                        {**row, "entry": json.dumps(row["entry"], ensure_ascii=False) if row["entry"] else ""}
                    )
        else:
            raise ValueError("Export format must be json or csv")

    def import_file(self, path: str, list_name: str = "default", format: str | None = None) -> int:
        self._validate_list(list_name)
        source = Path(path).expanduser()
        kind = (format or source.suffix.lstrip(".")).lower()
        if kind == "json":
            data = json.loads(source.read_text(encoding="utf-8"))
            rows = data.get("words", data) if isinstance(data, dict) else data
        elif kind == "csv":
            with source.open(newline="", encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))
        else:
            raise ValueError("Import format must be json or csv")
        if not isinstance(rows, list):
            raise ValueError("Import file must contain a list of words")
        count = 0
        for row in rows:
            if isinstance(row, str):
                self.add(list_name, row)
                count += 1
            elif isinstance(row, dict) and isinstance(row.get("word"), str):
                entry = row.get("entry")
                if isinstance(entry, str) and entry:
                    try:
                        entry = json.loads(entry)
                    except json.JSONDecodeError:
                        entry = None
                self.add(list_name, row["word"], entry if isinstance(entry, dict) else None)
                count += 1
        return count

    def flashcards(self, list_name: str = "default", client=None) -> tuple[list[dict[str, str]], int]:
        cards = []
        skipped = 0
        for row in self.list_words(list_name):
            entry = row["entry"]
            if entry is None and client is not None:
                try:
                    entry = client.define(row["word"])
                    self.add(list_name, row["word"], entry)
                except Exception:
                    entry = None
            definitions = entry.get("meanings", []) if isinstance(entry, dict) else []
            if not definitions and isinstance(entry, dict):
                definitions = [
                    definition.get("definition", "")
                    for meaning in entry.get("meaning_details", [])
                    for definition in meaning.get("definitions", [])
                ]
            definitions = [value for value in definitions if isinstance(value, str) and value.strip()]
            if not definitions:
                skipped += 1
                continue
            cards.append(
                {
                    "front": row["word"],
                    "back": "\n".join(definitions),
                    "sources": ",".join(entry.get("sources", [])),
                }
            )
        return cards, skipped

    def export_flashcards_file(self, path: str, list_name: str = "default", client=None) -> tuple[int, int]:
        cards, skipped = self.flashcards(list_name, client)
        target = Path(path).expanduser()
        kind = target.suffix.lower().lstrip(".")
        target.parent.mkdir(parents=True, exist_ok=True)
        if kind == "json":
            target.write_text(json.dumps(cards, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        elif kind == "csv":
            with target.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=["front", "back", "sources"])
                writer.writeheader()
                writer.writerows(cards)
        else:
            raise ValueError("Flashcard export filename must end in .json or .csv")
        return len(cards), skipped

    @staticmethod
    def _validate_list(list_name: str) -> None:
        if not list_name or len(list_name) > 80 or any(ord(char) < 32 for char in list_name):
            raise ValueError("List name must contain between 1 and 80 printable characters")
