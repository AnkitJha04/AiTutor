from __future__ import annotations

from fastapi import APIRouter, HTTPException
from typing import Any

from backend.api.schemas import QuestionsRequest
from backend.services.question_generator import QuestionGenerator
from backend.services.tutor_pipeline import TutorPipeline
from backend.utils.security import detect_prompt_injection, sanitize_text

router = APIRouter(tags=["questions"])


@router.post("/questions")
async def generate_questions(payload: QuestionsRequest) -> dict[str, Any]:
    pipeline = TutorPipeline()
    generator = QuestionGenerator()
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
        mcq = await generator.generate("mcq", chunks)
        short = await generator.generate("short", chunks)
        long = await generator.generate("long", chunks)
        if not mcq or not short or not long:
            raise ValueError("Failed to generate question content")
        return {"mcq": mcq, "short": short, "long": long}
    except Exception as exc:
        import logging
        logging.error(f"Questions generation error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Questions generation failed: {str(exc)}") from exc
