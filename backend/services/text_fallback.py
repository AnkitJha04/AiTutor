from __future__ import annotations

import re
from collections import Counter

from backend.rag.retriever import RetrievedChunk

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_WORD_RE = re.compile(r"[A-Za-z][A-Za-z\-']+")


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def _clean_chunk_text(text: str) -> str:
    text = re.sub(r"^[^\n]{0,120}\|Grade\s+\d+\s+\d+\s+", "", text)
    cleaned_lines: list[str] = []
    for line in text.splitlines():
        clean = re.sub(r"\s+", " ", line).strip()
        if not clean:
            continue
        lowered = clean.lower()
        if lowered == "chapter" or lowered.startswith("chapter "):
            continue
        if re.fullmatch(r"\d{1,4}", clean):
            continue
        cleaned_lines.append(clean)
    return " ".join(cleaned_lines).strip()


def _page_value(chunk: RetrievedChunk) -> int:
    value = chunk.metadata.get("page")
    try:
        return int(value) if value is not None else 0
    except Exception:
        return 0


def _sentences_from_text(text: str) -> list[str]:
    text = _clean_chunk_text(text)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    parts = [part.strip() for part in _SENTENCE_SPLIT.split(text) if part.strip()]
    if parts:
        return parts
    return [text]


def _collect_sentences(chunks: list[RetrievedChunk], limit: int = 6) -> list[tuple[str, int]]:
    collected: list[tuple[str, int]] = []
    seen: set[str] = set()
    for chunk in chunks:
        page = _page_value(chunk)
        for sentence in _sentences_from_text(chunk.text):
            normalized = _normalize(sentence)
            if len(sentence) < 40 or normalized in seen:
                continue
            if sentence.isdigit():
                continue
            seen.add(normalized)
            collected.append((sentence, page))
            if len(collected) >= limit:
                return collected
    return collected


def _collect_highlight_lines(chunks: list[RetrievedChunk], limit: int = 3) -> list[tuple[str, int]]:
    patterns = ("example", "activity", "suppose", "consider", "remember", "investigate")
    collected: list[tuple[str, int]] = []
    seen: set[str] = set()
    for chunk in chunks:
        page = _page_value(chunk)
        for sentence in _sentences_from_text(chunk.text):
            clean = re.sub(r"\s+", " ", sentence).strip()
            if len(clean) < 20:
                continue
            lowered = clean.lower()
            if not any(pattern in lowered for pattern in patterns):
                continue
            normalized = _normalize(clean)
            if normalized in seen:
                continue
            seen.add(normalized)
            collected.append((clean, page))
            if len(collected) >= limit:
                return collected
    return collected


def fallback_notes(chunks: list[RetrievedChunk]) -> str:
    # Collect more sentences for a detailed notes view
    sentences = _collect_sentences(chunks, limit=12)
    if not sentences:
        return "Information not present in textbook."
    lines = ["Textbook notes:"]
    # Bullet summary lines
    for sentence, page in sentences[:8]:
        citation = f"(Page {page})" if page else ""
        lines.append(f"- {sentence} {citation}".strip())

    # Add a short stitched paragraph for detail
    detail_sentences = [s for s, _ in sentences[:6]]
    if detail_sentences:
        paragraph = " ".join(detail_sentences)
        lines.append("")
        lines.append("Detailed summary:")
        lines.append(paragraph)
    return "\n".join(lines)


def fallback_questions(chunks: list[RetrievedChunk], kind: str) -> str:
    # Collect more candidate facts for detailed question generation
    sentences = _collect_sentences(chunks, limit=6)
    if not sentences:
        return "Information not present in textbook."
    if kind == "mcq":
        lines = ["Textbook quiz:"]
        for idx, (sentence, page) in enumerate(sentences[:6], start=1):
            citation = f"(Page {page})" if page else ""
            lines.append(f"{idx}. Which statement is directly supported by the textbook? {citation}".strip())
            lines.append(f"A. {sentence}")
            # pick two other distinct sentences as distractors when possible
            other_candidates = [s for s, _ in sentences if s != sentence]
            b = other_candidates[0] if len(other_candidates) > 0 else "This statement is not stated in the textbook."
            c = other_candidates[1] if len(other_candidates) > 1 else "This statement is not stated in the textbook."
            lines.append(f"B. {b}")
            lines.append(f"C. {c}")
            lines.append("D. This statement is not stated in the textbook.")
            lines.append("Correct answer: A")
            lines.append(f"Explanation: The textbook states: {sentence} {citation}".strip())
            lines.append("")
        return "\n".join(lines).strip()

    label = "Short answer" if kind == "short" else "Long answer"
    lines = [f"{label} questions:"]
    for idx, (sentence, page) in enumerate(sentences[:6], start=1):
        citation = f"(Page {page})" if page else ""
        if kind == "short" or idx < 3:
            lines.append(f"{idx}. Explain the textbook idea: {sentence} {citation}".strip())
        else:
            # Encourage use of multiple textbook sentences for long answers
            extra = " " + " ".join(s for s, _ in sentences[idx: idx + 3]) if len(sentences) > idx else ""
            lines.append(
                f"{idx}. Write a detailed answer using the textbook idea: {sentence}{extra} {citation}".strip()
            )
    return "\n".join(lines)


def fallback_examples(chunks: list[RetrievedChunk]) -> str:
    highlights = _collect_highlight_lines(chunks, limit=3)
    if not highlights:
        highlights = _collect_sentences(chunks, limit=3)
    if not highlights:
        return "Information not present in textbook."
    lines = ["Solved examples:"]
    for idx, (text, page) in enumerate(highlights, start=1):
        citation = f"(Page {page})" if page else ""
        lines.append(f"Example {idx}: {text} {citation}".strip())
        # Provide a step-like solution using nearby sentences when available
        lines.append(f"Solution: This is grounded in the textbook passage above {citation}".strip())
        # attempt to add a short reasoning sentence from subsequent sentences
        following = _collect_sentences(chunks, limit=6)
        if following:
            for s, p in following:
                if p == page and s not in (text,):
                    lines.append(f"Reasoning: {s} {citation}".strip())
                    break
        lines.append("")
    return "\n".join(lines).strip()
