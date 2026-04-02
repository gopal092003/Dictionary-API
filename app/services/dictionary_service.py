from app.utils.api_client import fetch_meanings, fetch_synonyms

def get_word_data(word: str):
    meanings = fetch_meanings(word)
    synonyms = fetch_synonyms(word)

    return {
        "word": word,
        "meanings": meanings,
        "synonyms": synonyms
    }