from __future__ import annotations

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

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

        @app.get("/", response_class=HTMLResponse)
        async def root() -> str:
                return """
                <!doctype html>
                <html lang="en">
                    <head>
                        <meta charset="utf-8" />
                        <meta name="viewport" content="width=device-width, initial-scale=1" />
                        <title>AI Tutor</title>
                        <style>
                            body {
                                font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                                margin: 0;
                                min-height: 100vh;
                                display: grid;
                                place-items: center;
                                background: linear-gradient(135deg, #0f172a, #1e293b);
                                color: #e2e8f0;
                            }
                            main {
                                max-width: 720px;
                                padding: 32px;
                            }
                            .card {
                                background: rgba(15, 23, 42, 0.72);
                                border: 1px solid rgba(148, 163, 184, 0.24);
                                border-radius: 20px;
                                padding: 32px;
                                box-shadow: 0 24px 80px rgba(15, 23, 42, 0.45);
                            }
                            h1 { margin: 0 0 12px; font-size: 2.2rem; }
                            p { line-height: 1.6; color: #cbd5e1; }
                            a {
                                color: #7dd3fc;
                                text-decoration: none;
                            }
                            .links {
                                display: flex;
                                flex-wrap: wrap;
                                gap: 12px;
                                margin-top: 20px;
                            }
                            .pill {
                                display: inline-block;
                                padding: 10px 14px;
                                border-radius: 999px;
                                background: rgba(125, 211, 252, 0.12);
                                border: 1px solid rgba(125, 211, 252, 0.25);
                            }
                        </style>
                    </head>
                    <body>
                        <main>
                            <section class="card">
                                <h1>AI Tutor is running</h1>
                                <p>
                                    This deployment exposes the FastAPI backend for textbook-grounded tutoring.
                                    Use the API routes under <a href="/docs">/docs</a> or check service health at
                                    <a href="/health">/health</a>.
                                </p>
                                <div class="links">
                                    <a class="pill" href="/health">Health</a>
                                    <a class="pill" href="/docs">API Docs</a>
                                    <span class="pill">Backend: FastAPI</span>
                                </div>
                            </section>
                        </main>
                    </body>
                </html>
                """

        @app.get("/health")
        async def health() -> dict[str, str]:
                return {"status": "ok"}

        return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
