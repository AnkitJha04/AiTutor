from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.api.schemas import TopicRequest
from backend.services.tutor_pipeline import TutorPipeline

router = APIRouter(tags=["subtopics"])


@router.post("/subtopics")
async def list_subtopics(payload: TopicRequest) -> dict[str, list[str]]:
    pipeline = TutorPipeline()
    try:
        subtopics = await pipeline.list_subtopics(
            payload.class_name,
            payload.subject,
            payload.book_title,
            payload.chapter_title,
            payload.topic_title,
        )
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"subtopics": subtopics}
