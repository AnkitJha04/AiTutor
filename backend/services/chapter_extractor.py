from __future__ import annotations

import re
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


def _heuristic_titles(text: str) -> list[str]:
    titles: list[str] = []
    pattern = re.compile(r"^(chapter|unit)\s+\d+(?:\s*[:\-]\s*)?(.*)$", re.IGNORECASE)
    for line in (line.strip() for line in text.splitlines() if line.strip()):
        match = pattern.match(line)
        if not match:
            continue
        title = (match.group(2) or line).strip()
        if title and title.lower() not in (item.lower() for item in titles):
            titles.append(title[:120])
    return titles or [line.strip() for line in text.splitlines() if line.strip()][:10]


async def extract_chapters_llm(text: str) -> list[str]:
    settings = get_settings()
    if settings.force_local_generation:
        return _heuristic_titles(text)
    client = OllamaClient(settings.ollama_base_url, settings.ollama_model)
    prompt_path = Path("prompts/chapters_prompt.txt")
    prompt = prompt_path.read_text(encoding="utf-8")
    context = text[: settings.chapter_max_chars]
    final_prompt = prompt.replace("{{context}}", context)
    try:
        response = await client.generate(final_prompt, temperature=settings.temperature)
    except Exception:
        return _heuristic_titles(text)

    if "Information not present in textbook." in response:
        return _heuristic_titles(text)

    titles = _parse_titles(response)
    return titles or _heuristic_titles(text)
