"""Conservative rule-based English morphology for common word forms."""

IRREGULAR = {
    "children": "child",
    "feet": "foot",
    "geese": "goose",
    "men": "man",
    "mice": "mouse",
    "teeth": "tooth",
    "women": "woman",
    "people": "person",
    "went": "go",
    "gone": "go",
    "did": "do",
    "done": "do",
    "was": "be",
    "were": "be",
    "been": "be",
    "had": "have",
    "has": "have",
    "made": "make",
    "saw": "see",
    "seen": "see",
    "ran": "run",
    "ate": "eat",
    "took": "take",
    "taken": "take",
    "better": "good",
    "best": "good",
    "worse": "bad",
    "worst": "bad",
}

IRREGULAR_NOUNS = {
    "child": "children",
    "foot": "feet",
    "goose": "geese",
    "man": "men",
    "mouse": "mice",
    "tooth": "teeth",
    "woman": "women",
    "person": "people",
}

IRREGULAR_VERBS = {
    "be": {"be", "am", "is", "are", "was", "were", "been", "being"},
    "do": {"do", "does", "did", "done", "doing"},
    "eat": {"eat", "eats", "ate", "eaten", "eating"},
    "go": {"go", "goes", "went", "gone", "going"},
    "have": {"have", "has", "had", "having"},
    "make": {"make", "makes", "made", "making"},
    "run": {"run", "runs", "ran", "running"},
    "see": {"see", "sees", "saw", "seen", "seeing"},
    "sit": {"sit", "sits", "sat", "sitting"},
    "take": {"take", "takes", "took", "taken", "taking"},
    "win": {"win", "wins", "won", "winning"},
}


def lemmatize(word: str) -> str:
    value = word.lower()
    if value in IRREGULAR:
        return IRREGULAR[value]
    for suffix, replacement in (
        ("ies", "y"),
        ("ves", "f"),
        ("ing", ""),
        ("ied", "y"),
        ("ed", ""),
        ("es", ""),
        ("s", ""),
        ("est", ""),
        ("er", ""),
    ):
        if value.endswith(suffix) and len(value) > len(suffix) + 2:
            candidate = value[: -len(suffix)] + replacement
            if suffix in {"ing", "ed"} and len(candidate) > 2 and candidate[-1] == candidate[-2]:
                candidate = candidate[:-1]
            elif suffix in {"ing", "ed"} and len(candidate) >= 3:
                consonant_vowel_consonant = (
                    candidate[-1] not in "aeiou" and candidate[-2] in "aeiou" and candidate[-3] not in "aeiou"
                )
                if consonant_vowel_consonant:
                    candidate += "e"
            return candidate
    return value


def _plural(noun: str) -> str:
    if noun in IRREGULAR_NOUNS:
        return IRREGULAR_NOUNS[noun]
    if noun.endswith(("s", "x", "z", "ch", "sh")):
        return noun + "es"
    if noun.endswith("y") and len(noun) > 1 and noun[-2] not in "aeiou":
        return noun[:-1] + "ies"
    if noun.endswith("fe"):
        return noun[:-2] + "ves"
    if noun.endswith("f"):
        return noun[:-1] + "ves"
    return noun + "s"


def _verb_forms(verb: str) -> set[str]:
    if verb in IRREGULAR_VERBS:
        return IRREGULAR_VERBS[verb]
    if verb.endswith("e"):
        past, gerund = verb + "d", verb[:-1] + "ing"
    elif len(verb) > 1 and verb.endswith("y") and verb[-2] not in "aeiou":
        past, gerund = verb[:-1] + "ied", verb + "ing"
    else:
        cvc = (
            len(verb) >= 3
            and verb[-1] not in "aeiouwxy"
            and verb[-2] in "aeiou"
            and verb[-3] not in "aeiou"
            and not verb.endswith(("en", "er", "el"))
        )
        stem = verb + verb[-1] if cvc else verb
        past, gerund = stem + "ed", stem + "ing"
    if len(verb) > 1 and verb.endswith("y") and verb[-2] not in "aeiou":
        third = verb[:-1] + "ies"
    else:
        ending = "es" if verb.endswith(("s", "x", "z", "ch", "sh", "o")) else "s"
        third = verb + ending
    return {verb, third, past, gerund}


def _adjective_forms(adjective: str) -> set[str]:
    if adjective in {"good", "bad"}:
        return {
            adjective,
            "better" if adjective == "good" else "worse",
            "best" if adjective == "good" else "worst",
        }
    if len(adjective) > 1 and adjective.endswith("y"):
        return {adjective, adjective[:-1] + "ier", adjective[:-1] + "iest"}
    stem = adjective[:-1] if adjective.endswith("e") else adjective
    return {adjective, stem + "er", stem + "est"}


def word_forms(word: str, part_of_speech: str | None = None) -> dict:
    lemma = lemmatize(word)
    pos = (part_of_speech or "").lower()
    if pos in {"noun", "n"}:
        forms = {lemma, _plural(lemma)}
    elif pos in {"verb", "v"}:
        forms = _verb_forms(lemma)
    elif pos in {"adjective", "adj"}:
        forms = _adjective_forms(lemma)
    else:
        forms = {lemma, _plural(lemma)} | _verb_forms(lemma) | _adjective_forms(lemma)
    return {
        "word": word,
        "lemma": lemma,
        "part_of_speech": pos or None,
        "forms": sorted(forms),
        "method": "local-heuristic",
    }
