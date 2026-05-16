from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.api.schemas import EvaluationRequest
from backend.evaluation.answer_validator import AnswerValidator
from backend.services.tutor_pipeline import TutorPipeline
from backend.utils.security import detect_prompt_injection, sanitize_text

router = APIRouter(tags=["evaluate"])


@router.post("/evaluate")
async def evaluate_answer(payload: EvaluationRequest) -> dict[str, str]:
    pipeline = TutorPipeline()
    validator = AnswerValidator()
    try:
        if detect_prompt_injection(payload.student_answer) or detect_prompt_injection(payload.question):
            raise ValueError("Unsafe input detected")
        question = sanitize_text(payload.question, max_len=1000)
        answer = sanitize_text(payload.student_answer, max_len=2000)
        store = await pipeline.build_book_index(
            payload.class_name, payload.subject, payload.book_title
        )
        topic = payload.topic_title or ""
        query = " - ".join([part for part in [topic, payload.chapter_title, question] if part])
        chunks = await pipeline.retrieve(query, store, chapter_title=payload.chapter_title)
        return await validator.validate(question, answer, chunks)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
