# Dictionary API

A local-first English dictionary service, Python library, and CLI. DictionaryAPI.dev supplies definitions and pronunciation metadata; Datamuse supplies word relationships, rhymes, search, and suggestions. The application runs on a developer's machine and does not require a hosted backend or paid service. A local word corpus and offline dictionary are optional and are not bundled.

## Install and run

Python 3.10 or newer:

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -e .
dictionary-api --help
```

Run the HTTP server with `python run.py` or `uvicorn app.main:app --reload`. By default it listens on `127.0.0.1:8000`. Interactive docs are at `/docs` and `/redoc`; the versioned API reference is [docs/v2.md](docs/v2.md).

## API

The existing `GET /` and `GET /define/{word}` routes remain supported. The complete additive API is under `/api/v2`:

| Route | Purpose |
|---|---|
| `GET /define/{word}?context=...` | Full entry; optional context token overlap reorders definitions without changing their text |
| `POST /define/batch` | Per-word results; one lookup failure does not fail other words |
| `GET /synonyms/{word}`, `/antonyms/{word}` | Merged dictionary and Datamuse results |
| `GET /related/{word}?kind=associations\|semantic\|similar` | Associated words, WordNet relations, or similar meanings |
| `GET /graph/{word}?depth=1` | Bounded relationship graph from Datamuse lexical relations |
| `GET /rhymes/{word}`, `/suggest/{word}` | Rhyming words and spelling suggestions |
| `GET /search?prefix=pre` | Prefix, wildcard, anagram, or length search with `limit` and `offset` |
| `GET /anagrams/{word}` | Anagrams from the optional local corpus |
| `GET /forms/{word}` | Local heuristic lemma and common forms |
| `GET /frequency/{word}` | Frequency from a configured corpus when supplied |
| `GET /random`, `/word-of-the-day` | Local corpus tools |
| `GET /health` | Application state; optional `check_providers=true` actually probes dependencies |

`/define` retains `word`, flat string-list `meanings`, and `synonyms` for existing clients. Structured definitions are available in `meaning_details`. Missing source data is represented as an empty list or `null`, never invented. New clients should use `/api/v2`.

Provider calls have finite timeouts and bounded retries. Unknown dictionary words return `404`, invalid input `422`, too-large batches `413`, and unavailable required dependencies or local corpora `503`. Datamuse outages do not prevent successful dictionary definitions. See [API v2 details](docs/v2.md).

## Configuration

All settings are optional; defaults work for local development.

| Variable | Default | Purpose |
|---|---|---|
| `DICTIONARY_API_URL` | `https://api.dictionaryapi.dev/api/v2/entries/en/` | Dictionary endpoint prefix |
| `DATAMUSE_API_URL` | `https://api.datamuse.com/words` | Datamuse word endpoint |
| `DATAMUSE_SUGGEST_URL` | `https://api.datamuse.com/sug` | Datamuse suggestions endpoint |
| `DATAMUSE_VOCABULARY` | unset | Optional Datamuse vocabulary, such as `es` |
| `DATAMUSE_API_KEY` | unset | Optional provider key |
| `PROVIDER_TIMEOUT_SECONDS` | `5` | Timeout per HTTP request |
| `PROVIDER_RETRIES` | `1` | Retries for timeout, connection, 429, and 5xx failures |
| `CACHE_BACKEND` | `memory` | `memory`, `sqlite`, or `none` |
| `CACHE_TTL_SECONDS` | `300` | Cache lifetime; zero disables writes |
| `SQLITE_CACHE_PATH` | `dictionary-cache.sqlite3` | SQLite cache file when selected |
| `VOCABULARY_DB_PATH` | `dictionary-vocabulary.sqlite3` | Personal vocabulary store |
| `WORD_CORPUS_PATH` | unset | Optional word/frequency file for local search and random tools |
| `OFFLINE_DICTIONARY_PATH` | unset | Optional user-supplied JSON Lines dictionary |
| `MAX_BATCH_SIZE` | `50` | Maximum words in a batch request |
| `HOST`, `PORT`, `RELOAD` | `127.0.0.1`, `8000`, `true` | Local development server binding |

Datamuse currently permits keyless basic use and has announced key enforcement starting February 1, 2027. Its documentation has not published the key transport format yet; this adapter currently passes a configured key as a `key` query parameter in one isolated location. Recheck provider documentation before relying on that mechanism. [Datamuse API documentation](https://www.datamuse.com/api/)

## Local corpus formats

`WORD_CORPUS_PATH` accepts UTF-8 text with one word per line. An optional tab-separated second column is a frequency per million words:

```text
apple	12.4
word
# comment lines are ignored
```

`OFFLINE_DICTIONARY_PATH` accepts one JSON object per line. A row has a `word` and optional fields such as `meanings` / `meaning_details`, `phonetics`, `synonyms`, `antonyms`, `origins`, and `frequency_per_million`. The offline adapter uses these records when the remote dictionary has no entry or is unavailable. No corpus is included because third-party datasets have separate redistribution terms; verify and document the license for data you provide.

```json
{"word":"quokka","meanings":[{"part_of_speech":"noun","definitions":[{"definition":"A small marsupial.","example":"A quokka smiled."}]}],"frequency_per_million":0.4}
```

## Python library and CLI

```python
from app import DictionaryClient, VocabularyStore

client = DictionaryClient()
entry = client.define("apple")
print(entry["meanings"])

VocabularyStore().add("study", "apple", entry)
```

Examples:

```sh
dictionary-api define apple
dictionary-api batch apple banana unknown
dictionary-api rhymes time --limit 15
dictionary-api search --prefix pre --limit 25
dictionary-api forms running --part-of-speech verb
dictionary-api vocab add apple --list study
dictionary-api vocab export study.json --list study
dictionary-api vocab import study.csv --list imported
dictionary-api vocab flashcards --list study --output study-cards.csv
```

`batch` prints one JSON result per word and exits with code `4` if any word fails, while still returning successful lookups. Batch size follows `MAX_BATCH_SIZE`.

Vocabulary lists are stored in SQLite and can be imported/exported as JSON or CSV. Flashcard exports use saved definitions, fetching and saving missing entries when possible; words with no available definitions are skipped. `DictionaryClient.clear_cache()` clears its configured cache. Rule-based morphology is intentionally lightweight and returns an approximate lemma; use a specialized optional NLP package if a project needs comprehensive linguistic analysis.

For language experiments, point `DICTIONARY_API_URL` at a compatible language endpoint and set `DATAMUSE_VOCABULARY` (Datamuse currently documents English and Spanish vocabularies). Provider adapters can also be injected into `DictionaryService` by downstream projects.

## Development and deployment

```sh
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check app tests
python -m ruff format --check app tests
python -m mypy app
```

Tests mock provider HTTP and do not need internet access. CI runs tests across Python 3.10–3.13, plus lint and typing checks. Docker is optional: `docker build -t local-dictionary-api .` then `docker run --rm -p 8000:8000 local-dictionary-api`.

Provider data remains subject to the provider's terms and attribution requirements. This project's code is MIT licensed; that license does not cover external provider content or user-supplied corpora. See [CONTRIBUTING.md](CONTRIBUTING.md), [compatibility policy](docs/compatibility.md), and [CHANGELOG.md](CHANGELOG.md).

## Provider attribution

Definitions and pronunciation data are served by [DictionaryAPI.dev](https://dictionaryapi.dev/). Word relationships, spelling suggestions, and rhyme data are served by the [Datamuse API](https://www.datamuse.com/api/). Public applications using Datamuse should acknowledge it in their documentation. Results can vary by provider, word, and language; this project relays provider content and does not claim ownership of it.
