from fastapi import FastAPI
from app.routes.dictionary import router

def create_app():
    app = FastAPI(
        title="Dictionary API",
        description="Search for word meanings and synonyms",
        version="1.0.0"
    )

    app.include_router(router)

    return app