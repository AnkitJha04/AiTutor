from __future__ import annotations

from pathlib import Path

from backend.config.settings import get_settings
from backend.models.ollama_client import OllamaClient
from backend.rag.retriever import RetrievedChunk


class AnswerValidator:
    def __init__(self) -> None:
        settings = get_settings()
        self.client = OllamaClient(settings.ollama_base_url, settings.ollama_model)
        self.temperature = settings.temperature
        self.prompt_path = Path("prompts/evaluation_prompt.txt")

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
        response = await self.client.generate(final_prompt, temperature=self.temperature)
        sources = ", ".join(str(c.metadata.get("page")) for c in chunks)
        source_chunks = "\n\n".join(
            f"[Page {c.metadata.get('page')}] {c.text}" for c in chunks
        )
        return {"content": response.strip(), "sources": sources, "source_chunks": source_chunks}
