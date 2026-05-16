from __future__ import annotations

from pydantic import BaseModel, Field


class BookRequest(BaseModel):
    class_name: str = Field(..., min_length=1)
    subject: str = Field(..., min_length=1)


class BookTitleRequest(BookRequest):
    book_title: str = Field(..., min_length=1)


class ChapterRequest(BookTitleRequest):
    chapter_title: str = Field(..., min_length=1)


class TopicRequest(ChapterRequest):
    topic_title: str = Field(..., min_length=1)


class SubtopicRequest(TopicRequest):
    subtopic_title: str = Field(..., min_length=1)


class NotesRequest(SubtopicRequest):
    pass


class QuestionsRequest(SubtopicRequest):
    difficulty: str = Field(default="medium")


class ExamplesRequest(SubtopicRequest):
    pass


class EvaluationRequest(SubtopicRequest):
    question: str = Field(..., min_length=1)
    student_answer: str = Field(..., min_length=1)
