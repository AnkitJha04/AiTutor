from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import fitz
import pdfplumber


@dataclass
class ChapterText:
    title: str
    content: str
    pages: list[int]


def _clean_text(text: str) -> str:
    text = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _clean_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _is_page_number(line: str) -> bool:
    return bool(re.fullmatch(r"\d{1,4}", line.strip()))


def _parse_contents_entries(lines: list[str]) -> list[tuple[int, str, int]]:
    chapter_line = re.compile(r"^Chapter\s+(\d+)(?:\s+(.+))?$", re.IGNORECASE)
    entries: list[tuple[int, str, int]] = []
    idx = 0
    while idx < len(lines):
        line = _clean_text(lines[idx])
        match = chapter_line.match(line)
        if not match:
            idx += 1
            continue

        chapter_number = int(match.group(1))
        title = (match.group(2) or "").strip()
        start_page = None

        probe = idx + 1
        while probe < len(lines):
            candidate = _clean_text(lines[probe])
            if not candidate:
                probe += 1
                continue
            if chapter_line.match(candidate):
                break
            if _is_page_number(candidate):
                start_page = int(candidate)
                break
            if not title and candidate.lower() not in {"contents", "foreword", "about this book"}:
                title = candidate
            probe += 1

        if title and start_page:
            entries.append((chapter_number, title, start_page))

        idx = probe if probe > idx else idx + 1

    return entries


def _extract_chapters_from_contents(doc: fitz.Document) -> list[ChapterText]:
    best_entries: dict[int, tuple[str, int]] = {}
    for page_number in range(1, doc.page_count + 1):
        lines = _clean_lines(doc.load_page(page_number - 1).get_text("text") or "")
        entries = _parse_contents_entries(lines)
        if len(entries) < 4:
            continue
        for chapter_number, title, start_page in entries:
            if chapter_number not in best_entries:
                best_entries[chapter_number] = (title, start_page)

    if len(best_entries) < 4:
        return []

    ordered_entries = sorted(best_entries.items(), key=lambda item: item[1][1])
    chapters: list[ChapterText] = []
    for idx, (_, (title, start_page)) in enumerate(ordered_entries):
        end_page = ordered_entries[idx + 1][1][1] - 1 if idx + 1 < len(ordered_entries) else doc.page_count
        if start_page > doc.page_count:
            continue
        pages = list(range(start_page, min(end_page, doc.page_count) + 1))
        page_texts = []
        for page_number in pages:
            page = doc.load_page(page_number - 1)
            page_texts.append(_clean_text(page.get_text("text")))
        chapters.append(
            ChapterText(
                title=title,
                content=" ".join(page_texts).strip(),
                pages=pages,
            )
        )
    return chapters


def extract_chapters(pdf_path: Path) -> list[ChapterText]:
    doc = fitz.open(str(pdf_path))
    contents_chapters = _extract_chapters_from_contents(doc)
    if contents_chapters:
        doc.close()
        return contents_chapters

    toc = doc.get_toc() or []
    if toc:
        chapters: list[ChapterText] = []
        min_level = min(item[0] for item in toc)
        top_level = [item for item in toc if item[0] == min_level]
        for idx, item in enumerate(top_level):
            title = item[1].strip()
            if not title:
                continue
            start_page = item[2]
            end_page = (
                top_level[idx + 1][2] - 1 if idx + 1 < len(top_level) else doc.page_count
            )
            pages = list(range(start_page, end_page + 1))
            page_texts = []
            for page_number in pages:
                page = doc.load_page(page_number - 1)
                page_texts.append(_clean_text(page.get_text("text")))
            chapters.append(
                ChapterText(
                    title=title,
                    content=" ".join(page_texts).strip(),
                    pages=pages,
                )
            )
        doc.close()
        if chapters:
            return chapters

    doc.close()

    chapters: list[ChapterText] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        current_title = None
        current_pages: list[int] = []
        current_text: list[str] = []

        for idx, page in enumerate(pdf.pages, start=1):
            raw = page.extract_text() or ""
            text = _clean_text(raw)
            match = re.search(r"\bchapter\s+\d+\b", text, re.IGNORECASE)
            if match:
                if current_title:
                    chapters.append(
                        ChapterText(
                            title=current_title,
                            content=" ".join(current_text).strip(),
                            pages=current_pages,
                        )
                    )
                current_title = text[:120].strip()
                current_pages = [idx]
                current_text = [text]
            else:
                if current_title:
                    current_pages.append(idx)
                    current_text.append(text)

        if current_title:
            chapters.append(
                ChapterText(
                    title=current_title,
                    content=" ".join(current_text).strip(),
                    pages=current_pages,
                )
            )
    if chapters:
        return chapters

    with fitz.open(str(pdf_path)) as doc:
        start_pattern = re.compile(r"^(chapter|unit)\s+\d+\b", re.IGNORECASE)
        title_pattern = re.compile(
            r"^(chapter|unit)\s+\d+\s*[:\-]?\s*(.+)", re.IGNORECASE
        )
        markers: list[tuple[int, str]] = []
        for page_number in range(1, doc.page_count + 1):
            page = doc.load_page(page_number - 1)
            raw_lines = _clean_lines(page.get_text("text") or "")[:8]
            title_line = next((line for line in raw_lines if start_pattern.match(line)), "")
            if not title_line:
                continue
            match = title_pattern.match(title_line)
            if match and match.group(2):
                title = _clean_text(match.group(2))
            else:
                title = _clean_text(title_line)
            markers.append((page_number, title[:120]))

        if markers:
            chapters = []
            for idx, (start_page, title) in enumerate(markers):
                end_page = (
                    markers[idx + 1][0] - 1 if idx + 1 < len(markers) else doc.page_count
                )
                pages = list(range(start_page, end_page + 1))
                page_texts = []
                for page_number in pages:
                    page = doc.load_page(page_number - 1)
                    page_texts.append(_clean_text(page.get_text("text")))
                chapters.append(
                    ChapterText(
                        title=title or f"Chapter {idx + 1}",
                        content=" ".join(page_texts).strip(),
                        pages=pages,
                    )
                )
            return chapters

    with fitz.open(str(pdf_path)) as doc:
        page_texts = []
        for page_number in range(1, doc.page_count + 1):
            page = doc.load_page(page_number - 1)
            page_texts.append(_clean_text(page.get_text("text")))
    content = " ".join([t for t in page_texts if t]).strip()
    pages = list(range(1, len(page_texts) + 1))
    return [ChapterText(title="Full Book", content=content, pages=pages)]


def extract_chapter(pdf_path: Path, chapter_title: str) -> ChapterText:
    chapters = extract_chapters(pdf_path)
    for chapter in chapters:
        if chapter_title.lower() in chapter.title.lower():
            return chapter
    if len(chapters) == 1:
        return chapters[0]
    raise ValueError("Chapter not found")


def extract_page_texts(pdf_path: Path, pages: Iterable[int]) -> list[tuple[int, str]]:
    page_texts: list[tuple[int, str]] = []
    with fitz.open(str(pdf_path)) as doc:
        for page_number in pages:
            page = doc.load_page(page_number - 1)
            text = _clean_text(page.get_text("text"))
            page_texts.append((page_number, text))
    return page_texts


def extract_toc_text(pdf_path: Path, max_pages: int = 12) -> str:
    toc_texts: list[str] = []
    with fitz.open(str(pdf_path)) as doc:
        page_count = doc.page_count
        scan_pages = list(range(1, min(max_pages, page_count) + 1))
        contents_hits: list[int] = []
        for page_number in scan_pages:
            page = doc.load_page(page_number - 1)
            text = _clean_text(page.get_text("text"))
            if text:
                toc_texts.append(text)
            if "contents" in text.lower():
                contents_hits.append(page_number)
        for hit in contents_hits:
            for extra in range(hit + 1, min(hit + 3, page_count) + 1):
                page = doc.load_page(extra - 1)
                text = _clean_text(page.get_text("text"))
                if text:
                    toc_texts.append(text)
    return " ".join(toc_texts).strip()


def extract_numbered_heading_entries(
    pdf_path: Path, pages: Iterable[int], depth: int
) -> list[tuple[int, str]]:
    if depth < 1:
        raise ValueError("depth must be at least 1")

    heading_pattern = re.compile(
        rf"^\d+(?:\.\d+){{{depth}}}\s+[A-Z].+"
    )
    entries: list[tuple[int, str]] = []
    seen: set[tuple[int, str]] = set()

    with fitz.open(str(pdf_path)) as doc:
        for page_number in pages:
            if page_number < 1 or page_number > doc.page_count:
                continue
            page = doc.load_page(page_number - 1)
            blocks = page.get_text("dict").get("blocks", [])
            for block in blocks:
                if "lines" not in block:
                    continue
                # Extract only the FIRST line from the block as the heading
                first_line = block["lines"][0] if block["lines"] else None
                if not first_line:
                    continue
                block_text = " ".join(
                    span["text"]
                    for span in first_line.get("spans", [])
                    if span.get("text")
                ).strip()
                if not block_text:
                    continue
                # Take only the part before significant whitespace (2+ spaces or newline)
                heading = re.split(r"\s{2,}|\n", block_text, maxsplit=1)[0]
                heading = _clean_text(heading)
                if not heading_pattern.match(heading):
                    continue
                if len(heading) > 80:  # Limit heading length
                    heading = heading[:80]
                key = (page_number, heading)
                if key in seen:
                    continue
                seen.add(key)
                entries.append((page_number, heading))

    return entries


def extract_heading_lines(
    pdf_path: Path,
    pages: Iterable[int],
    min_size: float = 12.0,
    max_words: int = 10,
) -> list[tuple[int, str, float]]:
    entries: list[tuple[int, str, float]] = []
    seen: set[tuple[int, str]] = set()

    with fitz.open(str(pdf_path)) as doc:
        for page_number in pages:
            if page_number < 1 or page_number > doc.page_count:
                continue
            page = doc.load_page(page_number - 1)
            for block in page.get_text("dict").get("blocks", []):
                lines = block.get("lines")
                if not lines:
                    continue
                
                # Process only the FIRST line from each block as potential heading
                first_line = lines[0]
                spans = first_line.get("spans", [])
                if not spans:
                    continue
                
                text = _clean_text(" ".join(span.get("text", "") for span in spans))
                if not text or _is_page_number(text):
                    continue
                
                size = max(float(span.get("size", 0.0)) for span in spans)
                if size < min_size:
                    continue
                
                if text.lower() == "chapter" or re.fullmatch(r"\d+", text):
                    continue
                # Stricter limits to avoid paragraph capture but more reasonable than before
                if len(text) > 120 or len(text.split()) > max_words:
                    continue
                
                key = (page_number, text)
                if key in seen:
                    continue
                seen.add(key)
                entries.append((page_number, text, size))

    return entries