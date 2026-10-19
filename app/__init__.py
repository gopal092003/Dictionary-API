"""Local-first dictionary API, library, and command line tools."""

from app.library import DictionaryClient
from app.vocabulary import VocabularyStore

__version__ = "2.0.0"

__all__ = ["DictionaryClient", "VocabularyStore", "__version__"]
