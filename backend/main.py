from __future__ import annotations

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import (
    books,
    chapters,
    subtopics,
    notes,
    questions,
    examples,
    evaluate,
    topics,
)
from backend.config.settings import get_settings
from backend.utils.logger import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(title="NCERT Grounded Tutor", version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(books.router, prefix="/api")
    app.include_router(topics.router, prefix="/api")
    app.include_router(chapters.router, prefix="/api")
    app.include_router(subtopics.router, prefix="/api")
    app.include_router(notes.router, prefix="/api")
    app.include_router(questions.router, prefix="/api")
    app.include_router(examples.router, prefix="/api")
    app.include_router(evaluate.router, prefix="/api")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
