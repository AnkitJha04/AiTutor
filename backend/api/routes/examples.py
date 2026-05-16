from __future__ import annotations

from fastapi import APIRouter, HTTPException
from typing import Any

from backend.api.schemas import ExamplesRequest
from backend.services.solved_examples import SolvedExamplesGenerator
from backend.services.tutor_pipeline import TutorPipeline
from backend.utils.security import detect_prompt_injection, sanitize_text

router = APIRouter(tags=["examples"])


@router.post("/examples")
async def generate_examples(payload: ExamplesRequest) -> dict[str, Any]:
    pipeline = TutorPipeline()
    generator = SolvedExamplesGenerator()
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
            raise ValueError("Failed to generate examples content")
        return result
    except Exception as exc:
        import logging
        logging.error(f"Examples generation error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Examples generation failed: {str(exc)}") from exc
