"""Environment-backed configuration for the local Dictionary API."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    dictionary_api_url: str = "https://api.dictionaryapi.dev/api/v2/entries/en/"
    datamuse_api_url: str = "https://api.datamuse.com/words"
    datamuse_suggest_url: str = "https://api.datamuse.com/sug"
    datamuse_vocabulary: str | None = None
    datamuse_api_key: str | None = None
    request_timeout: float = 5.0
    retry_count: int = 1
    cache_backend: str = "memory"
    cache_ttl_seconds: int = 300
    sqlite_cache_path: str = "dictionary-cache.sqlite3"
    vocabulary_db_path: str = "dictionary-vocabulary.sqlite3"
    word_corpus_path: str | None = None
    offline_dictionary_path: str | None = None
    max_batch_size: int = 50

    @classmethod
    def from_env(cls) -> "Settings":
        settings = cls(
            dictionary_api_url=os.getenv("DICTIONARY_API_URL", cls.dictionary_api_url),
            datamuse_api_url=os.getenv("DATAMUSE_API_URL", cls.datamuse_api_url),
            datamuse_suggest_url=os.getenv("DATAMUSE_SUGGEST_URL", cls.datamuse_suggest_url),
            datamuse_vocabulary=os.getenv("DATAMUSE_VOCABULARY") or None,
            datamuse_api_key=os.getenv("DATAMUSE_API_KEY") or None,
            request_timeout=float(os.getenv("PROVIDER_TIMEOUT_SECONDS", "5")),
            retry_count=max(0, int(os.getenv("PROVIDER_RETRIES", "1"))),
            cache_backend=os.getenv("CACHE_BACKEND", "memory").lower(),
            cache_ttl_seconds=max(0, int(os.getenv("CACHE_TTL_SECONDS", "300"))),
            sqlite_cache_path=os.getenv("SQLITE_CACHE_PATH", "dictionary-cache.sqlite3"),
            vocabulary_db_path=os.getenv("VOCABULARY_DB_PATH", "dictionary-vocabulary.sqlite3"),
            word_corpus_path=os.getenv("WORD_CORPUS_PATH") or None,
            offline_dictionary_path=os.getenv("OFFLINE_DICTIONARY_PATH") or None,
            max_batch_size=max(1, int(os.getenv("MAX_BATCH_SIZE", "50"))),
        )
        if settings.cache_backend not in {"memory", "sqlite", "none"}:
            raise ValueError("CACHE_BACKEND must be memory, sqlite, or none")
        if settings.request_timeout <= 0:
            raise ValueError("PROVIDER_TIMEOUT_SECONDS must be positive")
        return settings


settings = Settings.from_env()

# Backward-compatible constants for users of the original small API module.
DICTIONARY_API = settings.dictionary_api_url.rstrip("/") + "/"
DATAMUSE_API = settings.datamuse_api_url.rstrip("/")
DATAMUSE_API_KEY = settings.datamuse_api_key
REQUEST_TIMEOUT = settings.request_timeout
RETRY_COUNT = settings.retry_count
