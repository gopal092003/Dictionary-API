import requests
from app.config.settings import DICTIONARY_API, SYNONYM_API

def fetch_meanings(word: str):
    response = requests.get(DICTIONARY_API + word)

    if response.status_code != 200:
        raise ValueError(f"Word '{word}' not found")

    data = response.json()
    meanings = []

    try:
        for meaning in data[0]["meanings"]:
            for definition in meaning["definitions"]:
                meanings.append(definition["definition"])
    except Exception:
        meanings.append("No meanings found")

    return meanings


def fetch_synonyms(word: str):
    response = requests.get(SYNONYM_API + word)

    if response.status_code != 200:
        return []

    return [item["word"] for item in response.json()]