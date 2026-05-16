from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.api.schemas import BookTitleRequest
from backend.services.tutor_pipeline import TutorPipeline

router = APIRouter(tags=["chapters"])


@router.post("/chapters")
async def list_chapters(payload: BookTitleRequest) -> dict[str, str | list[str]]:
    pipeline = TutorPipeline()
    index_status = "ok"
    index_error = ""
    try:
        chapters = await pipeline.list_chapters(
            payload.class_name, payload.subject, payload.book_title
        )
        try:
            await pipeline.build_book_index(
                payload.class_name, payload.subject, payload.book_title
            )
        except Exception as exc:
            index_status = "error"
            index_error = str(exc) or f"Indexing failed: {type(exc).__name__}"
    except Exception as exc:
        detail = str(exc) or f"{type(exc).__name__}"
        raise HTTPException(status_code=404, detail=detail) from exc
    return {
        "chapters": chapters,
        "index_status": index_status,
        "index_error": index_error,
    }
