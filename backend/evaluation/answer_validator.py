from __future__ import annotations

import re
from pathlib import Path

from backend.config.settings import get_settings
from backend.models.ollama_client import OllamaClient
from backend.rag.retriever import RetrievedChunk


class AnswerValidator:
    def __init__(self) -> None:
        settings = get_settings()
        self.settings = settings
        self.client = None if settings.force_local_generation else OllamaClient(settings.ollama_base_url, settings.ollama_model)
        self.temperature = settings.temperature
        self.prompt_path = Path("prompts/evaluation_prompt.txt")

    def _local_validate(self, question: str, student_answer: str, chunks: list[RetrievedChunk]) -> str:
        context = " ".join(chunk.text for chunk in chunks)
        question_terms = set(re.findall(r"[A-Za-z][A-Za-z\-']+", question.lower()))
        answer_terms = set(re.findall(r"[A-Za-z][A-Za-z\-']+", student_answer.lower()))
        context_terms = set(re.findall(r"[A-Za-z][A-Za-z\-']+", context.lower()))

        supported = sorted((answer_terms | question_terms) & context_terms)
        coverage = len(supported) / max(1, len(answer_terms | question_terms))
        if not student_answer.strip():
            verdict = "The answer is empty."
        elif coverage >= 0.4:
            verdict = "The answer is well supported by the textbook context."
        elif coverage >= 0.15:
            verdict = "The answer is partially supported by the textbook context."
        else:
            verdict = "The answer has weak support from the textbook context."

        support_text = ", ".join(supported[:12]) if supported else "none"
        return (
            f"{verdict}\n"
            f"Matched terms: {support_text}\n"
            f"Question: {question[:240]}"
        )

    async def validate(
        self, question: str, student_answer: str, chunks: list[RetrievedChunk]
    ) -> dict[str, str]:
        if not chunks:
            return {
                "content": "Information not present in textbook.",
                "sources": "",
                "source_chunks": "",
            }
        prompt = self.prompt_path.read_text(encoding="utf-8")
        context = "\n\n".join(
            f"[Page {c.metadata.get('page')}] {c.text}" for c in chunks
        )
        final_prompt = (
            prompt.replace("{{context}}", context)
            .replace("{{question}}", question)
            .replace("{{answer}}", student_answer)
        )
        sources = ", ".join(str(c.metadata.get("page")) for c in chunks)
        source_chunks = "\n\n".join(
            f"[Page {c.metadata.get('page')}] {c.text}" for c in chunks
        )
        if self.client is not None:
            try:
                response = await self.client.generate(final_prompt, temperature=self.temperature)
                return {"content": response.strip(), "sources": sources, "source_chunks": source_chunks}
            except Exception:
                pass

        return {
            "content": self._local_validate(question, student_answer, chunks),
            "sources": sources,
            "source_chunks": source_chunks,
        }
