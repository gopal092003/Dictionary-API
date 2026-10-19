"""Compatibility helpers for callers of the original API client module."""

import requests  # re-exported so existing request mocks remain compatible

from app.config.settings import DATAMUSE_API, DICTIONARY_API
from app.providers.datamuse import DatamuseProvider
from app.providers.dictionary_api import DictionaryApiProvider
from app.providers.http import ProviderError, WordNotFound

__all__ = [
    "requests",
    "DATAMUSE_API",
    "DICTIONARY_API",
    "ProviderError",
    "WordNotFound",
    "fetch_antonyms",
    "fetch_dictionary_entry",
    "fetch_meanings",
    "fetch_phonetics",
    "fetch_synonyms",
]


def fetch_dictionary_entry(word: str) -> dict:
    return DictionaryApiProvider().lookup(word)


def fetch_meanings(word: str) -> list[str]:
    return DictionaryApiProvider().lookup(word)["meanings"]


def fetch_phonetics(word: str) -> list[dict]:
    return DictionaryApiProvider().lookup(word)["phonetics"]


def fetch_synonyms(word: str) -> list[str]:
    return DatamuseProvider().relation(word, "syn")


def fetch_antonyms(word: str) -> list[str]:
    return DatamuseProvider().relation(word, "ant")
