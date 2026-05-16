from __future__ import annotations

import re
import json
from pathlib import Path

from backend.config.settings import get_settings
from backend.models.ollama_client import OllamaClient


def extract_subtopics(text: str) -> list[dict[str, str]]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    subtopics: list[dict[str, str]] = []
    current_title = None
    current_content: list[str] = []

    numbered_heading = re.compile(r"^\d+(?:\.\d+)*\s+[A-Z].+")
    title_heading = re.compile(r"^[A-Z][A-Za-z0-9\s\-:(),'/]{3,80}$")

    def flush() -> None:
        nonlocal current_title, current_content
        if current_title:
            subtopics.append({"title": current_title, "content": " ".join(current_content).strip()})
        current_title = None
        current_content = []

    for line in lines:
        is_heading = False
        if numbered_heading.match(line):
            is_heading = True
        elif title_heading.match(line) and len(line.split()) <= 10 and not line.endswith((".", ";", ",")):
            is_heading = True

        if is_heading:
            flush()
            current_title = line
        else:
            current_content.append(line)

    flush()
    return subtopics


async def extract_subtopics_llm(chapter_title: str, text: str) -> list[dict[str, str]]:
    settings = get_settings()
    client = OllamaClient(settings.ollama_base_url, settings.ollama_model)
    prompt_path = Path("prompts/subtopics_prompt.txt")
    prompt = prompt_path.read_text(encoding="utf-8")
    context = text[: settings.subtopic_max_chars]
    final_prompt = (
        prompt.replace("{{chapter_title}}", chapter_title)
        .replace("{{context}}", context)
    )
    response = await client.generate(final_prompt, temperature=settings.temperature)

    if "Information not present in textbook." in response:
        return []

    titles: list[str] = []
    try:
        payload = json.loads(response.strip())
        if isinstance(payload, list):
            titles = [str(item).strip() for item in payload if str(item).strip()]
    except json.JSONDecodeError:
        lines = [line.strip("- ").strip() for line in response.splitlines()]
        titles = [line for line in lines if line]

    return [{"title": title, "content": ""} for title in titles]
