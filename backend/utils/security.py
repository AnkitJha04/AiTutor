from __future__ import annotations

import re
from urllib.parse import urlparse


def sanitize_text(value: str, max_len: int = 500) -> str:
    clean = re.sub(r"[\x00-\x1f\x7f]", "", value).strip()
    return clean[:max_len]


def is_safe_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"}


def detect_prompt_injection(text: str) -> bool:
    lowered = text.lower()
    triggers = ["ignore previous", "system prompt", "developer message", "jailbreak"]
    return any(t in lowered for t in triggers)
