from __future__ import annotations

from pathlib import Path
import json

from backend.config.settings import get_settings
from backend.models.ollama_client import OllamaClient
from backend.rag.retriever import RetrievedChunk
from backend.services.text_fallback import fallback_notes


class NotesGenerator:
    def __init__(self) -> None:
        settings = get_settings()
        self.client = None
        if not settings.force_local_generation:
            self.client = OllamaClient(settings.ollama_base_url, settings.ollama_model)
        self.temperature = settings.temperature
        self.prompt_path = Path("prompts/notes_prompt.txt")

    async def generate(self, chunks: list[RetrievedChunk]) -> dict[str, str]:
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
        final_prompt = prompt.replace("{{context}}", context)
        response = ""
        settings = get_settings()
        structured = None
        if not settings.force_local_generation and self.client is not None:
            # Ask model to return structured JSON
            json_prompt = final_prompt + (
                "\n\nRespond ONLY with JSON matching this schema:\n"
                "{\n  \"overview\": \"string\",\n  \"key_points\": [\"string\"],\n  \"detailed_paragraphs\": [\"string\"],\n  \"important_terms\": [\"string\"]\n}\n"
            )
            try:
                response = await self.client.generate(json_prompt, temperature=self.temperature)
                parsed = json.loads(response)
                # basic validation
                if isinstance(parsed, dict) and parsed.get("overview"):
                    structured = parsed
            except Exception:
                response = ""
                structured = None

        sources = ", ".join(str(c.metadata.get("page")) for c in chunks)
        source_chunks = "\n\n".join(
            f"[Page {c.metadata.get('page')}] {c.text}" for c in chunks
        )

        if structured is not None:
            return {"content": structured, "sources": sources, "source_chunks": source_chunks}

        # fallback: use textbook-only structured notes
        fallback_text = fallback_notes(chunks)
        # try to convert fallback into structured shape
        structured_fb = {
            "overview": "",
            "key_points": [],
            "detailed_paragraphs": [],
            "important_terms": [],
        }
        parts = [p.strip() for p in fallback_text.split('\n\n') if p.strip()]
        if parts:
            structured_fb["overview"] = parts[0]
        # collect bullet lines as key points
        bullets = [line[2:].strip() for line in fallback_text.splitlines() if line.startswith("- ")]
        structured_fb["key_points"] = bullets[:8]
        # detailed paragraphs
        structured_fb["detailed_paragraphs"] = parts[1:3]
        structured_fb["important_terms"] = [t.split()[0] for t in bullets[:6]]
        return {"content": structured_fb, "sources": sources, "source_chunks": source_chunks}
