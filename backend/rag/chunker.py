from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Chunk:
    text: str
    metadata: dict[str, str | int | None]


def chunk_text(
    page_texts: list[tuple[int, str]],
    chapter: str,
    subtopic: str | None,
    chunk_size: int = 800,
    overlap: int = 120,
) -> list[Chunk]:
    chunks: list[Chunk] = []
    step = max(1, chunk_size - overlap)

    for page, text in page_texts:
        words = text.split()
        if not words:
            continue
        for start in range(0, len(words), step):
            chunk_words = words[start : start + chunk_size]
            if not chunk_words:
                continue
            chunk_text_value = " ".join(chunk_words)
            chunks.append(
                Chunk(
                    text=chunk_text_value,
                    metadata={"page": page, "chapter": chapter, "subtopic": subtopic},
                )
            )
    return chunks
