"""HTTP API routes. The router is mounted both at root and under /api/v2."""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from app.config.settings import settings
from app.local_data import CorpusUnavailable
from app.models.dictionary import (
    AntonymResponse,
    BatchRequest,
    BatchResponse,
    FormResponse,
    FrequencyResponse,
    HealthResponse,
    HomeResponse,
    RandomWordResponse,
    RelatedResponse,
    RelationshipGraphResponse,
    RhymeResponse,
    SearchResponse,
    SuggestionResponse,
    SynonymResponse,
    WordEntry,
    WordOfDayResponse,
)
from app.providers.http import ProviderError, WordNotFound
from app.services.dictionary_service import DictionaryService, InvalidWord, create_default_service

router = APIRouter()
service: DictionaryService = create_default_service()


def _raise_http(exc: Exception) -> None:
    if isinstance(exc, InvalidWord):
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if isinstance(exc, WordNotFound):
        raise HTTPException(status_code=404, detail="Word not found") from exc
    if isinstance(exc, CorpusUnavailable):
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if isinstance(exc, ProviderError):
        raise HTTPException(status_code=503, detail="A required provider is temporarily unavailable") from exc
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    raise exc


@router.get("/", response_model=HomeResponse, tags=["health"])
def home():
    return {"message": "Dictionary API is running", "usage": "/define/{word}", "api_version": "v2"}


@router.get("/health", response_model=HealthResponse, tags=["health"])
def health(check_providers: bool = False):
    return service.health(check_providers=check_providers)


@router.post("/define/batch", response_model=BatchResponse, tags=["dictionary"])
def define_batch(request: BatchRequest):
    if not request.words:
        raise HTTPException(status_code=422, detail="Provide at least one word")
    if len(request.words) > settings.max_batch_size:
        raise HTTPException(status_code=413, detail=f"Batch size cannot exceed {settings.max_batch_size}")
    results = []
    for word in request.words:
        try:
            results.append({"word": word, "ok": True, "entry": service.define(word), "error": None})
        except (InvalidWord, WordNotFound, ProviderError, CorpusUnavailable) as exc:
            results.append({"word": word, "ok": False, "entry": None, "error": str(exc)})
    return {"results": results}


@router.get("/define/{word}", response_model=WordEntry, tags=["dictionary"])
def define_word(word: str, context: str | None = Query(None, max_length=500)):
    try:
        return service.define(word, context)
    except Exception as exc:
        _raise_http(exc)


@router.get("/synonyms/{word}", response_model=SynonymResponse, tags=["relationships"])
def synonyms(word: str, limit: int = Query(100, ge=1, le=100)):
    try:
        return service.synonyms(word, limit)
    except Exception as exc:
        _raise_http(exc)


@router.get("/antonyms/{word}", response_model=AntonymResponse, tags=["relationships"])
def antonyms(word: str, limit: int = Query(100, ge=1, le=100)):
    try:
        return service.antonyms(word, limit)
    except Exception as exc:
        _raise_http(exc)


@router.get("/related/{word}", response_model=RelatedResponse, tags=["relationships"])
def related(word: str, kind: str = "associations", limit: int = Query(20, ge=1, le=100)):
    try:
        return service.related(word, kind, limit)
    except Exception as exc:
        _raise_http(exc)


@router.get("/graph/{word}", response_model=RelationshipGraphResponse, tags=["relationships"])
def relationship_graph(word: str, depth: int = Query(1, ge=1, le=2), limit: int = Query(50, ge=1, le=100)):
    try:
        return service.relationship_graph(word, depth, limit)
    except Exception as exc:
        _raise_http(exc)


@router.get("/rhymes/{word}", response_model=RhymeResponse, tags=["relationships"])
def rhymes(word: str, limit: int = Query(20, ge=1, le=100)):
    try:
        return service.rhymes(word, limit)
    except Exception as exc:
        _raise_http(exc)


@router.get("/suggest/{word}", response_model=SuggestionResponse, tags=["word intelligence"])
def suggest(word: str, limit: int = Query(10, ge=1, le=100)):
    try:
        return service.suggest(word, limit)
    except Exception as exc:
        _raise_http(exc)


@router.get("/search", response_model=SearchResponse, tags=["word intelligence"])
def search(
    prefix: str | None = None,
    pattern: str | None = None,
    anagram: str | None = None,
    length: int | None = Query(None, ge=1, le=80),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0, le=10000),
):
    try:
        return service.search(
            prefix=prefix, pattern=pattern, anagram=anagram, length=length, limit=limit, offset=offset
        )
    except Exception as exc:
        _raise_http(exc)


@router.get("/anagrams/{word}", response_model=SearchResponse, tags=["word intelligence"])
def anagrams(word: str, limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0)):
    try:
        return service.search(anagram=word, limit=limit, offset=offset)
    except Exception as exc:
        _raise_http(exc)


@router.get("/forms/{word}", response_model=FormResponse, tags=["word intelligence"])
def forms(word: str, part_of_speech: str | None = None):
    try:
        return service.forms(word, part_of_speech)
    except Exception as exc:
        _raise_http(exc)


@router.get("/frequency/{word}", response_model=FrequencyResponse, tags=["word intelligence"])
def frequency(word: str):
    try:
        return service.frequency(word)
    except Exception as exc:
        _raise_http(exc)


@router.get("/random", response_model=RandomWordResponse, tags=["local corpus"])
def random_word():
    try:
        return {"word": service.random_word()["word"], "sources": ["local-corpus"]}
    except Exception as exc:
        _raise_http(exc)


@router.get("/word-of-the-day", response_model=WordOfDayResponse, tags=["local corpus"])
def word_of_the_day():
    try:
        utc_today = datetime.now(timezone.utc).date()
        return service.word_of_day(utc_today)
    except Exception as exc:
        _raise_http(exc)
