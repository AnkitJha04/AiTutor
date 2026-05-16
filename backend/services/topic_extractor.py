from __future__ import annotations

import json
from pathlib import Path

from backend.config.settings import get_settings
from backend.models.ollama_client import OllamaClient
from backend.services.subtopic_extractor import extract_subtopics


def _parse_titles(response: str) -> list[str]:
    try:
        payload = json.loads(response.strip())
        if isinstance(payload, list):
            return [str(item).strip() for item in payload if str(item).strip()]
    except json.JSONDecodeError:
        pass
    lines = [line.strip("- ").strip() for line in response.splitlines()]
    return [line for line in lines if line]


async def extract_topics(chapter_title: str, text: str) -> list[str]:
    settings = get_settings()
    client = OllamaClient(settings.ollama_base_url, settings.ollama_model)
    prompt_path = Path("prompts/topics_prompt.txt")
    prompt = prompt_path.read_text(encoding="utf-8")
    context = text[: settings.chapter_max_chars]
    final_prompt = (
        prompt.replace("{{chapter_title}}", chapter_title)
        .replace("{{context}}", context)
    )
    try:
        response = await client.generate(final_prompt, temperature=settings.temperature)
    except Exception:
        response = ""

    if "Information not present in textbook." in response:
        return []
    titles = _parse_titles(response)
    if titles:
        return titles

    heuristic = extract_subtopics(text)
    return [item["title"] for item in heuristic if item.get("title")]
