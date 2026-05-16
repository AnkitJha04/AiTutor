from __future__ import annotations

import json
from pathlib import Path

from backend.config.settings import get_settings
from backend.models.ollama_client import OllamaClient


def _parse_titles(response: str) -> list[str]:
    try:
        payload = json.loads(response.strip())
        if isinstance(payload, list):
            return [str(item).strip() for item in payload if str(item).strip()]
    except json.JSONDecodeError:
        pass
    lines = [line.strip("- ").strip() for line in response.splitlines()]
    return [line for line in lines if line]


async def extract_chapters_llm(text: str) -> list[str]:
    settings = get_settings()
    client = OllamaClient(settings.ollama_base_url, settings.ollama_model)
    prompt_path = Path("prompts/chapters_prompt.txt")
    prompt = prompt_path.read_text(encoding="utf-8")
    context = text[: settings.chapter_max_chars]
    final_prompt = prompt.replace("{{context}}", context)
    response = await client.generate(final_prompt, temperature=settings.temperature)

    if "Information not present in textbook." in response:
        return []

    titles = _parse_titles(response)
    return titles
