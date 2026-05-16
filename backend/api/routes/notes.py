from __future__ import annotations

from fastapi import APIRouter, HTTPException
from typing import Any

from backend.api.schemas import NotesRequest
from backend.services.notes_generator import NotesGenerator
from backend.services.tutor_pipeline import TutorPipeline
from backend.utils.security import detect_prompt_injection, sanitize_text

router = APIRouter(tags=["notes"])


@router.post("/notes")
async def generate_notes(payload: NotesRequest) -> dict[str, Any]:
    pipeline = TutorPipeline()
    generator = NotesGenerator()
    try:
        if detect_prompt_injection(payload.subtopic_title):
            raise ValueError("Unsafe input detected")
        topic = sanitize_text(payload.topic_title)
        subtopic = sanitize_text(payload.subtopic_title)
        chunks = await pipeline.get_subtopic_chunks(
            payload.class_name,
            payload.subject,
            payload.book_title,
            payload.chapter_title,
            topic,
            subtopic,
        )
        result = await generator.generate(chunks)
        if not result or not result.get('content'):
            raise ValueError("Failed to generate notes content")
        return result
    except Exception as exc:
        import logging
        logging.error(f"Notes generation error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Notes generation failed: {str(exc)}") from exc
