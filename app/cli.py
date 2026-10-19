"""Command-line interface for the reusable local dictionary client."""

import argparse
import json
import sys

from app.config.settings import settings
from app.library import DictionaryClient
from app.providers.http import ProviderError, WordNotFound
from app.vocabulary import VocabularyStore


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dictionary-api", description="Local-first dictionary tools")
    sub = parser.add_subparsers(dest="command", required=True)
    commands = (
        "define",
        "synonyms",
        "antonyms",
        "related",
        "rhymes",
        "suggest",
        "forms",
        "frequency",
        "anagrams",
        "graph",
    )
    for command in commands:
        child = sub.add_parser(command)
        child.add_argument("word")
        if command in {"related", "forms"}:
            child.add_argument("--kind", default="associations")
            child.add_argument("--part-of-speech", dest="part_of_speech")
        child.add_argument("--limit", type=int, default=20)
        if command == "define":
            child.add_argument("--context")
        if command == "graph":
            child.add_argument("--depth", type=int, default=1)

    search = sub.add_parser("search")
    query = search.add_mutually_exclusive_group(required=True)
    query.add_argument("--prefix")
    query.add_argument("--pattern")
    query.add_argument("--anagram")
    query.add_argument("--length", type=int)
    search.add_argument("--limit", type=int, default=20)
    search.add_argument("--offset", type=int, default=0)
    batch = sub.add_parser("batch", help="Define multiple words in one command")
    batch.add_argument("words", nargs="+", help="Words to look up")
    sub.add_parser("random")
    sub.add_parser("word-of-the-day")
    cache = sub.add_parser("cache")
    cache_actions = cache.add_subparsers(dest="cache_command", required=True)
    cache_actions.add_parser("clear")

    vocab = sub.add_parser("vocab")
    vocab.add_argument("--db", default=settings.vocabulary_db_path)
    actions = vocab.add_subparsers(dest="vocab_command", required=True)
    add = actions.add_parser("add")
    add.add_argument("word")
    add.add_argument("--list", default="default")
    remove = actions.add_parser("remove")
    remove.add_argument("word")
    remove.add_argument("--list", default="default")
    listing = actions.add_parser("list")
    listing.add_argument("--list", default="default")
    for action in ("import", "export"):
        file_action = actions.add_parser(action)
        file_action.add_argument("path")
        file_action.add_argument("--list", default="default")
        file_action.add_argument("--format", choices=("json", "csv"))
    flashcards = actions.add_parser("flashcards")
    flashcards.add_argument("--list", default="default")
    flashcards.add_argument("--output", required=True)
    return parser


def _run(args: argparse.Namespace) -> object:
    if args.command == "vocab":
        store = VocabularyStore(args.db)
        if args.vocab_command == "add":
            store.add(args.list, args.word)
            return {"added": args.word, "list": args.list}
        if args.vocab_command == "remove":
            return {"removed": store.remove(args.list, args.word), "word": args.word}
        if args.vocab_command == "list":
            return store.list_words(args.list)
        if args.vocab_command == "import":
            return {"imported": store.import_file(args.path, args.list, args.format), "list": args.list}
        if args.vocab_command == "flashcards":
            count, skipped = store.export_flashcards_file(args.output, args.list, client=DictionaryClient())
            return {"exported": args.output, "cards": count, "skipped_without_definitions": skipped}
        store.export_file(args.path, args.list, args.format)
        return {"exported": args.path, "list": args.list}

    if args.command == "cache":
        if settings.cache_backend == "sqlite":
            from app.cache import SQLiteCache

            SQLiteCache(settings.sqlite_cache_path).clear()
            return {"cleared": True, "backend": "sqlite"}
        return {
            "cleared": False,
            "backend": settings.cache_backend,
            "message": "There is no persistent cache to clear from this process",
        }

    client = DictionaryClient()
    if args.command == "batch":
        return client.define_batch(args.words)
    if args.command == "define":
        return client.define(args.word, args.context)
    if args.command == "synonyms":
        return client.synonyms(args.word, args.limit)
    if args.command == "antonyms":
        return client.antonyms(args.word, args.limit)
    if args.command == "related":
        return client.related(args.word, args.kind, args.limit)
    if args.command == "rhymes":
        return client.rhymes(args.word, args.limit)
    if args.command == "suggest":
        return client.suggest(args.word, args.limit)
    if args.command == "forms":
        return client.forms(args.word, args.part_of_speech)
    if args.command == "frequency":
        return client.frequency(args.word)
    if args.command == "anagrams":
        return client.search(anagram=args.word, limit=args.limit)
    if args.command == "graph":
        return client.relationship_graph(args.word, args.depth, args.limit)
    if args.command == "search":
        return client.search(
            prefix=args.prefix,
            pattern=args.pattern,
            anagram=args.anagram,
            length=args.length,
            limit=args.limit,
            offset=args.offset,
        )
    if args.command == "random":
        return client.random_word()
    return client.word_of_day()


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = _run(args)
    except WordNotFound as exc:
        print(str(exc) or "Word not found", file=sys.stderr)
        return 2
    except ProviderError as exc:
        print(f"Provider unavailable: {exc}", file=sys.stderr)
        return 3
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if (
        args.command == "batch"
        and isinstance(result, list)
        and any(isinstance(item, dict) and item.get("ok") is False for item in result)
    ):
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
