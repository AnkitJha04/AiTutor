from __future__ import annotations

from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

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

ROOT_DIR = Path(__file__).resolve().parents[1]
FRONTEND_DIST_DIR = ROOT_DIR / "frontend" / "dist"
FRONTEND_INDEX = FRONTEND_DIST_DIR / "index.html"


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

    def serve_frontend() -> FileResponse:
        if not FRONTEND_INDEX.exists():
            raise HTTPException(status_code=500, detail="Frontend build not found")
        return FileResponse(FRONTEND_INDEX)

    if FRONTEND_DIST_DIR.exists():
        assets_dir = FRONTEND_DIST_DIR / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

        @app.get("/", include_in_schema=False)
        async def root() -> FileResponse:
            return serve_frontend()

        @app.get("/{full_path:path}", include_in_schema=False)
        async def spa_fallback(full_path: str) -> FileResponse:
            if full_path.startswith(("api/", "docs", "redoc", "openapi.json", "health", "assets/")):
                raise HTTPException(status_code=404)
            return serve_frontend()
    else:
        @app.get("/", include_in_schema=False)
        async def root() -> dict[str, str]:
            return {"status": "ok", "detail": "Frontend build not found"}

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
