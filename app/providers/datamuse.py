from app.config.settings import settings
from app.providers.http import ProviderError, get_json

RELATIONS = {"syn", "ant", "rhy", "trg", "jja", "jjb", "spc", "gen", "com", "par", "hom", "cns"}


class DatamuseProvider:
    name = "datamuse"

    def __init__(
        self,
        words_url: str | None = None,
        suggest_url: str | None = None,
        api_key: str | None = settings.datamuse_api_key,
        vocabulary: str | None = settings.datamuse_vocabulary,
        timeout: float | None = None,
        retries: int | None = None,
    ):
        self.words_url = (words_url or settings.datamuse_api_url).rstrip("/")
        self.suggest_url = suggest_url or settings.datamuse_suggest_url
        self.api_key = api_key
        self.vocabulary = vocabulary
        self.timeout = timeout if timeout is not None else settings.request_timeout
        self.retries = retries if retries is not None else settings.retry_count

    def _words(self, params: dict) -> list[str]:
        if self.vocabulary:
            params["v"] = self.vocabulary
        if self.api_key:
            # Isolated here because the provider has announced key enforcement but
            # has not yet documented the final transport mechanism.
            params["key"] = self.api_key
        data = get_json(self.words_url, params=params, timeout=self.timeout, retries=self.retries)
        if not isinstance(data, list):
            raise ProviderError("Datamuse returned malformed data")
        return [row["word"] for row in data if isinstance(row, dict) and isinstance(row.get("word"), str)]

    def relation(self, word: str, relation: str, limit: int = 100) -> list[str]:
        if relation == "ml":
            param = "ml"
        elif relation in RELATIONS:
            param = "rel_" + relation
        else:
            raise ValueError(f"Unsupported Datamuse relation: {relation}")
        return self._words({param: word, "max": min(max(limit, 1), 1000)})

    def suggest(self, word: str, limit: int = 10) -> list[str]:
        params = {"s": word, "max": min(max(limit, 1), 1000)}
        if self.vocabulary:
            params["v"] = self.vocabulary
        if self.api_key:
            params["key"] = self.api_key
        data = get_json(self.suggest_url, params=params, timeout=self.timeout, retries=self.retries)
        if not isinstance(data, list):
            raise ProviderError("Datamuse returned malformed suggestions")
        return [row["word"] for row in data if isinstance(row, dict) and isinstance(row.get("word"), str)]

    def search(
        self, *, prefix: str | None = None, pattern: str | None = None, limit: int = 20, offset: int = 0
    ) -> list[str]:
        spell = pattern if pattern is not None else f"{prefix}*"
        maximum = min(max(limit + offset, 1), 1000)
        return self._words({"sp": spell, "max": maximum})[offset : offset + limit]
