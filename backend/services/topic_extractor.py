from __future__ import annotations

import re
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


def _heuristic_topics(text: str, chapter_title: str) -> list[str]:
    titles: list[str] = []
    chapter_norm = chapter_title.strip().lower()
    heading_pattern = re.compile(r"^(?:\d+(?:\.\d+)*\s+)?[A-Z][A-Za-z0-9\s\-:(),'/]{3,120}$")
    for line in (line.strip() for line in text.splitlines() if line.strip()):
        if not heading_pattern.match(line):
            continue
        if line.lower().startswith(("chapter", "contents", "exercise")):
            continue
        if line.endswith((".", ";", ",")):
            continue
        cleaned = re.sub(r"^\d+(?:\.\d+)*\s+", "", line).strip()
        if not cleaned or cleaned.lower() == chapter_norm:
            continue
        if cleaned.lower() not in (item.lower() for item in titles):
            titles.append(cleaned[:120])
    return titles


async def extract_topics(chapter_title: str, text: str) -> list[str]:
    settings = get_settings()
    if settings.force_local_generation:
        return _heuristic_topics(text, chapter_title)
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
        return _heuristic_topics(text, chapter_title)

    if "Information not present in textbook." in response:
        return _heuristic_topics(text, chapter_title)
    titles = _parse_titles(response)
    if titles:
        return titles

    heuristic = extract_subtopics(text)
    fallback = [item["title"] for item in heuristic if item.get("title")]
    return fallback or _heuristic_topics(text, chapter_title)
