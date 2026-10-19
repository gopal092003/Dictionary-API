from pydantic import BaseModel


class Phonetic(BaseModel):
    text: str | None = None
    audio: str | None = None


class Definition(BaseModel):
    definition: str
    example: str | None = None


class Meaning(BaseModel):
    part_of_speech: str | None = None
    definitions: list[Definition]


class WordEntry(BaseModel):
    """Stable HTTP response. `meanings` remains flat for legacy clients."""

    word: str
    meanings: list[str]
    synonyms: list[str]
    phonetics: list[Phonetic]
    meaning_details: list[Meaning]
    antonyms: list[str]
    related_words: list[str]
    origins: list[str]
    sources: list[str]
    frequency_per_million: float | None = None
    ranking: str | None = None


class SynonymResponse(BaseModel):
    word: str
    synonyms: list[str]
    sources: list[str]


class AntonymResponse(BaseModel):
    word: str
    antonyms: list[str]
    sources: list[str]


class RelatedResponse(BaseModel):
    word: str
    kind: str
    related_words: list[str]
    sources: list[str]


class RhymeResponse(BaseModel):
    word: str
    rhymes: list[str]
    sources: list[str]


class SuggestionResponse(BaseModel):
    word: str
    suggestions: list[str]
    sources: list[str]


class RandomWordResponse(BaseModel):
    word: str
    sources: list[str]


class SearchResponse(BaseModel):
    results: list[str]
    limit: int
    offset: int
    sources: list[str]


class FormResponse(BaseModel):
    word: str
    lemma: str
    part_of_speech: str | None = None
    forms: list[str]
    method: str
    sources: list[str]


class FrequencyResponse(BaseModel):
    word: str
    frequency_per_million: float | None
    sources: list[str]


class WordOfDayResponse(BaseModel):
    date: str
    word: str
    sources: list[str]


class GraphNode(BaseModel):
    id: str
    depth: int


class GraphEdge(BaseModel):
    source: str
    target: str
    relation: str


class RelationshipGraphResponse(BaseModel):
    root: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    sources: list[str]


class BatchItem(BaseModel):
    word: str
    ok: bool
    entry: WordEntry | None = None
    error: str | None = None


class BatchResponse(BaseModel):
    results: list[BatchItem]


class BatchRequest(BaseModel):
    words: list[str]


class HealthResponse(BaseModel):
    application: str
    providers: dict[str, str]
    offline_dictionary_configured: bool
    offline_corpus_available: bool
    cache: str


class HomeResponse(BaseModel):
    message: str
    usage: str
    api_version: str
