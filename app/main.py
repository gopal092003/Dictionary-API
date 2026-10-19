from fastapi import FastAPI

from app.routes.dictionary import router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Dictionary API",
        description="A local-first dictionary API with pluggable providers and optional offline data.",
        version="2.0.0",
    )
    app.include_router(router)
    # Versioned routes are additive; legacy unversioned routes remain supported.
    app.include_router(router, prefix="/api/v2")
    return app


app = create_app()
