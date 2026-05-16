from __future__ import annotations

from pathlib import Path
import json

from backend.config.settings import get_settings
from backend.models.ollama_client import OllamaClient
from backend.rag.retriever import RetrievedChunk
from backend.services.text_fallback import fallback_questions


class QuestionGenerator:
    def __init__(self) -> None:
        settings = get_settings()
        self.client = None
        if not settings.force_local_generation:
            self.client = OllamaClient(settings.ollama_base_url, settings.ollama_model)
        self.temperature = settings.temperature
        self.prompt_paths = {
            "mcq": Path("prompts/mcq_prompt.txt"),
            "short": Path("prompts/short_answer_prompt.txt"),
            "long": Path("prompts/long_answer_prompt.txt"),
        }

    async def generate(self, kind: str, chunks: list[RetrievedChunk]) -> dict[str, str]:
        if not chunks:
            return {
                "content": "Information not present in textbook.",
                "sources": "",
                "source_chunks": "",
            }
        prompt_path = self.prompt_paths[kind]
        prompt = prompt_path.read_text(encoding="utf-8")
        context = "\n\n".join(
            f"[Page {c.metadata.get('page')}] {c.text}" for c in chunks
        )
        final_prompt = prompt.replace("{{context}}", context)
        response = ""
        settings = get_settings()
        structured = None
        if not settings.force_local_generation and self.client is not None:
            # Structured JSON for questions: {mcq:[{q,options,answer,explanation}], short:[{q}], long:[{q}]}
            json_prompt = final_prompt + (
                "\n\nRespond ONLY with JSON matching this schema:\n"
                "{\n  \"mcq\": [{\"question\":\"string\",\"options\":[\"string\"],\"answer\":\"string\",\"explanation\":\"string\"}],\n  \"short\": [{\"question\":\"string\"}],\n  \"long\": [{\"question\":\"string\"}]\n}\n"
            )
            try:
                response = await self.client.generate(json_prompt, temperature=self.temperature)
                parsed = json.loads(response)
                if isinstance(parsed, dict) and (parsed.get("mcq") or parsed.get("short") or parsed.get("long")):
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

        # fallback
        fallback_text = fallback_questions(chunks, kind)
        # Try to convert fallback into structured shape when model not used
        if kind == "mcq":
            mcqs = []
            for part in [p.strip() for p in fallback_text.split('\n\n') if p.strip()]:
                if part.lower().startswith("textbook mcqs"):
                    continue
                # split by Question lines
                import re

                blocks = re.split(r"Question\s+\d+:?", part)
                for b in blocks:
                    b = b.strip()
                    if not b:
                        continue
                    lines = [l.strip() for l in b.splitlines() if l.strip()]
                    question_line = lines[0] if lines else ""
                    options = [l.split('.', 1)[1].strip() for l in lines if re.match(r'^[A-D]\.', l)]
                    answer_line = next((l for l in lines if l.lower().startswith("correct answer:")), "")
                    explanation = next((l for l in lines if l.lower().startswith("explanation:")), "")
                    answer = ""
                    if answer_line:
                        ans = answer_line.split(':', 1)[1].strip()
                        # map letter to option
                        if ans and options:
                            if len(ans) == 1 and ans.upper() in list("ABCD"):
                                idx = ord(ans.upper()) - ord('A')
                                if 0 <= idx < len(options):
                                    answer = options[idx]
                            else:
                                answer = ans
                    if question_line and options:
                        mcqs.append({"question": question_line, "options": options, "answer": answer, "explanation": explanation})
            if mcqs:
                return {"content": {"mcq": mcqs}, "sources": sources, "source_chunks": source_chunks}
        else:
            # short/long: collect up to 3 prompts
            prompts = []
            for line in fallback_text.splitlines():
                line = line.strip()
                if not line:
                    continue
                if line[0].isdigit() and line[1:3] == '. ':
                    prompts.append(line.split('.', 1)[1].strip())
                elif line.lower().startswith('short') or line.lower().startswith('long'):
                    continue
                else:
                    # heuristic: lines that end with ?
                    if line.endswith('?') and len(prompts) < 3:
                        prompts.append(line)
            if prompts:
                key = "short" if kind == "short" else "long"
                return {"content": {key: [{"question": p} for p in prompts[:3]]}, "sources": sources, "source_chunks": source_chunks}

        return {"content": fallback_text, "sources": sources, "source_chunks": source_chunks}
