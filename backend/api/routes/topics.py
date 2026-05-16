from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.api.schemas import ChapterRequest
from backend.services.tutor_pipeline import TutorPipeline

router = APIRouter(tags=["topics"])


@router.post("/topics")
async def list_topics(payload: ChapterRequest) -> dict[str, list[str]]:
    pipeline = TutorPipeline()
    try:
        topics = await pipeline.list_topics(
            payload.class_name, payload.subject, payload.book_title, payload.chapter_title
        )
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"topics": topics}
