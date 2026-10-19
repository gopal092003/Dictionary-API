"""Provider orchestration, local word intelligence, and result caching."""

import difflib
import logging
import re
from datetime import date, datetime, timezone

from app.cache import Cache, MemoryCache, NoCache, SQLiteCache
from app.config.settings import Settings, settings
from app.local_data import CorpusUnavailable, WordCorpus
from app.morphology import word_forms
from app.providers.datamuse import DatamuseProvider
from app.providers.dictionary_api import DictionaryApiProvider
from app.providers.http import ProviderError, WordNotFound
from app.providers.offline_dictionary import OfflineDictionaryProvider

logger = logging.getLogger(__name__)
WORD_PATTERN = re.compile(r"^[A-Za-z]+(?:[ '-][A-Za-z]+)*$")


class InvalidWord(ValueError):
    """The requested input is not a supported word or phrase."""


def normalize_word(word: str) -> str:
    normalized = " ".join(word.strip().split()).lower()
    if not normalized or len(normalized) > 80 or not WORD_PATTERN.fullmatch(normalized):
        raise InvalidWord("Word must contain letters, spaces, apostrophes, or hyphens only")
    return normalized


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result = []
    for value in values:
        folded = value.casefold().strip()
        if folded and folded not in seen:
            seen.add(folded)
            result.append(value.strip())
    return result


def build_cache(config: Settings = settings) -> Cache:
    if config.cache_backend == "none":
        return NoCache()
    if config.cache_backend == "sqlite":
        return SQLiteCache(config.sqlite_cache_path)
    return MemoryCache()


class DictionaryService:
    def __init__(
        self,
        *,
        dictionary_provider=None,
        relationship_provider=None,
        offline_provider=None,
        cache: Cache | None = None,
        corpus: WordCorpus | None = None,
        config: Settings = settings,
    ):
        self.dictionary_provider = dictionary_provider or DictionaryApiProvider(
            base_url=config.dictionary_api_url, timeout=config.request_timeout, retries=config.retry_count
        )
        self.relationship_provider = relationship_provider or DatamuseProvider(
            words_url=config.datamuse_api_url,
            suggest_url=config.datamuse_suggest_url,
            api_key=config.datamuse_api_key,
            vocabulary=config.datamuse_vocabulary,
            timeout=config.request_timeout,
            retries=config.retry_count,
        )
        self.offline_provider = offline_provider or OfflineDictionaryProvider(config.offline_dictionary_path)
        self.cache = cache or build_cache(config)
        self.corpus = corpus or WordCorpus(config.word_corpus_path, self.offline_provider.frequencies)
        self.cache_ttl = config.cache_ttl_seconds

    def _cached(self, key: str, getter):
        try:
            value = self.cache.get(key)
            if value is not None:
                return value
        except Exception as exc:
            logger.warning("Cache read failed", extra={"cache_key": key, "error_type": type(exc).__name__})
        value = getter()  # Failed responses are never cached.
        try:
            self.cache.set(key, value, self.cache_ttl)
        except Exception as exc:
            logger.warning("Cache write failed", extra={"cache_key": key, "error_type": type(exc).__name__})
        return value

    def _dictionary_entry(self, word: str) -> dict:
        cache_key = f"dictionary:{word}"
        try:
            return self._cached(cache_key, lambda: self.dictionary_provider.lookup(word))
        except (WordNotFound, ProviderError) as remote_error:
            try:
                local = self.offline_provider.lookup(word)
                return local
            except WordNotFound:
                raise remote_error

    def _remote_relation(self, word: str, relation: str, limit: int) -> list[str]:
        key = f"datamuse:{relation}:{word}:{limit}"
        return self._cached(key, lambda: self.relationship_provider.relation(word, relation, limit))

    def define(self, word: str, context: str | None = None) -> dict:
        normalized = normalize_word(word)
        entry = self._dictionary_entry(normalized)
        synonyms = list(entry.get("synonyms", []))
        antonyms = list(entry.get("antonyms", []))
        related: list[str] = []
        sources = list(entry.get("sources", [getattr(self.dictionary_provider, "name", "dictionary")]))
        datamuse_ok = False
        for relation, destination in (("syn", synonyms), ("ant", antonyms), ("trg", related)):
            try:
                destination.extend(self._remote_relation(normalized, relation, 100))
                datamuse_ok = True
            except ProviderError as exc:
                logger.warning(
                    "Optional relationship lookup failed",
                    extra={"word": normalized, "relation": relation, "error_type": type(exc).__name__},
                )
        if datamuse_ok and "datamuse" not in sources:
            sources.append("datamuse")
        result = dict(entry)
        result.update(
            {
                "word": normalized,
                "synonyms": _unique(synonyms),
                "antonyms": _unique(antonyms),
                "related_words": _unique(related),
                "sources": sources,
            }
        )
        if context is not None:
            if len(context) > 500:
                raise InvalidWord("Context must be 500 characters or fewer")
            tokens = set(re.findall(r"[a-z]+", context.lower()))
            if tokens:
                indexed = list(enumerate(result.get("meaning_details", [])))
                indexed.sort(
                    key=lambda pair: (
                        -sum(
                            len(tokens & set(re.findall(r"[a-z]+", definition.get("definition", "").lower())))
                            for definition in pair[1].get("definitions", [])
                        ),
                        pair[0],
                    )
                )
                result["meaning_details"] = [meaning for _, meaning in indexed]
                result["meanings"] = [
                    definition["definition"]
                    for meaning in result["meaning_details"]
                    for definition in meaning["definitions"]
                ]
            result["ranking"] = "context-token-overlap"
        return result

    def synonyms(self, word: str, limit: int = 100) -> dict:
        normalized = normalize_word(word)
        local, sources = [], []
        dictionary_error: Exception | None = None
        remote_error: Exception | None = None
        try:
            entry = self._dictionary_entry(normalized)
            local.extend(entry.get("synonyms", []))
            sources.extend(entry.get("sources", []))
        except (WordNotFound, ProviderError) as exc:
            dictionary_error = exc
        try:
            remote = self._remote_relation(normalized, "syn", limit)
            sources.append("datamuse")
        except ProviderError as exc:
            remote = []
            remote_error = exc
        if dictionary_error is not None and remote_error is not None:
            if isinstance(dictionary_error, WordNotFound):
                raise dictionary_error
            raise ProviderError("No synonym provider is available") from remote_error
        return {"word": normalized, "synonyms": _unique(local + remote)[:limit], "sources": _unique(sources)}

    def antonyms(self, word: str, limit: int = 100) -> dict:
        normalized = normalize_word(word)
        local, sources = [], []
        dictionary_error: Exception | None = None
        try:
            entry = self._dictionary_entry(normalized)
            local.extend(entry.get("antonyms", []))
            sources.extend(entry.get("sources", []))
        except (WordNotFound, ProviderError) as exc:
            dictionary_error = exc
        try:
            remote = self._remote_relation(normalized, "ant", limit)
            sources.append("datamuse")
        except ProviderError:
            remote = []
        if not local and not remote:
            # Empty relationships are valid; distinguish them from total provider failure.
            if not sources:
                if dictionary_error is not None and not isinstance(dictionary_error, ProviderError):
                    raise dictionary_error
                raise ProviderError("No configured provider could return antonyms")
        return {"word": normalized, "antonyms": _unique(local + remote)[:limit], "sources": _unique(sources)}

    def related(self, word: str, kind: str = "associations", limit: int = 20) -> dict:
        normalized = normalize_word(word)
        relations = {
            "associations": ("trg", "jja", "jjb"),
            "semantic": ("spc", "gen", "com", "par"),
            "similar": ("ml",),
        }
        codes = relations.get(kind, (kind,))
        values = []
        successful = 0
        errors = []
        for code in codes:
            try:
                values.extend(self._remote_relation(normalized, code, limit))
                successful += 1
            except ProviderError as exc:
                errors.append(exc)
        if successful == 0 and errors:
            raise ProviderError("Datamuse could not return related words") from errors[0]
        return {
            "word": normalized,
            "kind": kind,
            "related_words": _unique(values)[:limit],
            "sources": ["datamuse"],
        }

    def relationship_graph(self, word: str, depth: int = 1, limit: int = 50) -> dict:
        normalized = normalize_word(word)
        if depth not in {1, 2}:
            raise InvalidWord("Graph depth must be 1 or 2")
        relations = ("syn", "ant", "trg", "spc", "gen")
        nodes = {normalized: 0}
        edges = set()
        frontier = [normalized]
        successful = 0
        errors = []
        for level in range(1, depth + 1):
            next_frontier: list[str] = []
            for source in frontier:
                for relation in relations:
                    try:
                        values = self._remote_relation(source, relation, min(limit, 20))
                        successful += 1
                    except ProviderError as exc:
                        errors.append(exc)
                        continue
                    for target in values:
                        target = target.lower()
                        if target == source:
                            continue
                        if target not in nodes:
                            if len(nodes) >= limit:
                                continue
                            nodes[target] = level
                            if level < depth and len(next_frontier) < 10:
                                next_frontier.append(target)
                        edges.add((source, target, relation))
            frontier = next_frontier
        if successful == 0 and errors:
            raise ProviderError("Datamuse could not build a relationship graph") from errors[0]
        return {
            "root": normalized,
            "nodes": [{"id": node, "depth": node_depth} for node, node_depth in nodes.items()],
            "edges": [
                {"source": source, "target": target, "relation": relation}
                for source, target, relation in sorted(edges)
            ],
            "sources": ["datamuse"],
        }

    def rhymes(self, word: str, limit: int = 20) -> dict:
        normalized = normalize_word(word)
        values = self._remote_relation(normalized, "rhy", limit)
        return {"word": normalized, "rhymes": _unique(values)[:limit], "sources": ["datamuse"]}

    def suggest(self, word: str, limit: int = 10) -> dict:
        normalized = normalize_word(word)
        source = "datamuse"
        provider_failed = False
        try:
            values = self._cached(
                f"datamuse:suggest:{normalized}:{limit}",
                lambda: self.relationship_provider.suggest(normalized, limit),
            )
        except ProviderError:
            values = []
            provider_failed = True
        if not values and self.corpus.available:
            candidates = difflib.get_close_matches(
                normalized, list(self.corpus.words()), n=limit, cutoff=0.55
            )
            values, source = candidates, "local-corpus"
        if provider_failed and not self.corpus.available:
            raise ProviderError("No suggestion provider is available")
        return {"word": normalized, "suggestions": values[:limit], "sources": [source] if values else []}

    def search(
        self,
        *,
        prefix: str | None = None,
        pattern: str | None = None,
        anagram: str | None = None,
        length: int | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict:
        if sum(value is not None for value in (prefix, pattern, anagram, length)) != 1:
            raise InvalidWord("Provide exactly one of prefix, pattern, anagram, or length")
        if pattern is not None and not re.fullmatch(r"[A-Za-z*?]+", pattern):
            raise InvalidWord("Pattern may contain letters, * and ? only")
        if prefix is not None:
            prefix = normalize_word(prefix)
        if anagram is not None:
            anagram = normalize_word(anagram)
        if self.corpus.available:
            try:
                values = self.corpus.search(
                    prefix=prefix, pattern=pattern, anagram=anagram, length=length, limit=limit, offset=offset
                )
                return {"results": values, "limit": limit, "offset": offset, "sources": ["local-corpus"]}
            except CorpusUnavailable:
                pass
        if anagram is not None or length is not None:
            raise CorpusUnavailable(
                "Anagram and word-length search require WORD_CORPUS_PATH or an offline dictionary"
            )
        values = self.relationship_provider.search(prefix=prefix, pattern=pattern, limit=limit, offset=offset)
        return {"results": values, "limit": limit, "offset": offset, "sources": ["datamuse"]}

    def forms(self, word: str, part_of_speech: str | None = None) -> dict:
        normalized = normalize_word(word)
        result = word_forms(normalized, part_of_speech)
        result["sources"] = ["local-morphology"]
        return result

    def random_word(self) -> dict:
        return {"word": self.corpus.random_word(), "sources": ["local-corpus"]}

    def word_of_day(self, for_date: date | None = None) -> dict:
        date_value = for_date or datetime.now(timezone.utc).date()
        value = date_value.isoformat()
        return {"date": value, "word": self.corpus.word_of_day(value), "sources": ["local-corpus"]}

    def frequency(self, word: str) -> dict:
        normalized = normalize_word(word)
        value = self.corpus.frequency(normalized)
        if normalized not in self.corpus.words():
            raise WordNotFound
        return {"word": normalized, "frequency_per_million": value, "sources": ["local-corpus"]}

    def health(self, check_providers: bool = False) -> dict:
        providers = {"dictionary": "not_checked", "datamuse": "not_checked"}
        if check_providers:
            try:
                self.dictionary_provider.lookup("example")
                providers["dictionary"] = "healthy"
            except WordNotFound:
                providers["dictionary"] = "reachable_word_missing"
            except ProviderError:
                providers["dictionary"] = "unavailable"
            try:
                self.relationship_provider.relation("example", "syn", 1)
                providers["datamuse"] = "healthy"
            except ProviderError:
                providers["datamuse"] = "unavailable"
        return {
            "application": "ok",
            "providers": providers,
            "offline_dictionary_configured": self.offline_provider.available,
            "offline_corpus_available": self.corpus.available,
            "cache": type(self.cache).__name__,
        }


def create_default_service(config: Settings = settings) -> DictionaryService:
    offline = OfflineDictionaryProvider(config.offline_dictionary_path)
    return DictionaryService(
        config=config,
        offline_provider=offline,
        corpus=WordCorpus(config.word_corpus_path, offline.frequencies),
    )


_default_service = create_default_service()


def get_word_data(word: str) -> dict:
    """Backward-compatible service function used by the original route."""
    return _default_service.define(word)
