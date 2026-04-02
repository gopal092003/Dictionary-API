from fastapi import APIRouter, HTTPException
from app.services.dictionary_service import get_word_data

router = APIRouter()

@router.get("/")
def home():
    return {
        "message": "Dictionary API is running 🚀",
        "usage": "/define/{word}"
    }

@router.get("/define/{word}")
def define_word(word: str):
    try:
        return get_word_data(word)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")