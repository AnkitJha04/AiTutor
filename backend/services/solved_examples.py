from __future__ import annotations

from pathlib import Path
import json

from backend.config.settings import get_settings
from backend.models.ollama_client import OllamaClient
from backend.rag.retriever import RetrievedChunk
from backend.services.text_fallback import fallback_examples


class SolvedExamplesGenerator:
    def __init__(self) -> None:
        settings = get_settings()
        self.client = None
        if not settings.force_local_generation:
            self.client = OllamaClient(settings.ollama_base_url, settings.ollama_model)
        self.temperature = settings.temperature
        self.prompt_path = Path("prompts/solved_examples_prompt.txt")

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
            # Structured JSON for examples: [{problem, steps:[], final_answer, page}]
            json_prompt = final_prompt + (
                "\n\nRespond ONLY with JSON matching this schema:\n"
                "[{\"problem\":\"string\",\"steps\":[\"string\"],\"final_answer\":\"string\",\"page\":\"int\"}]\n"
            )
            try:
                response = await self.client.generate(json_prompt, temperature=self.temperature)
                parsed = json.loads(response)
                if isinstance(parsed, list) and parsed:
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

        fallback_text = fallback_examples(chunks)
        # try to parse fallback_text into structured examples
        examples = []
        import re
        parts = [p.strip() for p in fallback_text.split('\n\n') if p.strip()]
        for p in parts:
            m = re.match(r"Example\s*(\d+):\s*(.*)", p)
            if m:
                prob = m.group(2).strip()
                # find Solution and Reasoning lines
                lines = p.splitlines()
                sol = next((l for l in lines if l.lower().startswith('solution:')), '')
                reasoning = next((l for l in lines if l.lower().startswith('reasoning:')), '')
                steps = []
                if sol:
                    steps.append(sol.split(':', 1)[1].strip())
                if reasoning:
                    steps.append(reasoning.split(':', 1)[1].strip())
                examples.append({"problem": prob, "steps": steps, "final_answer": sol.split(':',1)[1].strip() if sol else '', "page": None})
        if examples:
            return {"content": examples[:3], "sources": sources, "source_chunks": source_chunks}
        return {"content": fallback_text, "sources": sources, "source_chunks": source_chunks}
