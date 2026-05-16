from __future__ import annotations

import re
from collections import Counter

import numpy as np
from dataclasses import dataclass

from backend.config.settings import get_settings
from backend.database.vector_store import VectorStore
from backend.rag.chunker import chunk_text
from backend.rag.embedder import Embedder
from backend.rag.retriever import Retriever, RetrievedChunk
from backend.scraping.ncert_scraper import NCERTScraper
from backend.scraping.pdf_processor import (
    extract_chapter,
    extract_chapters,
    extract_heading_lines,
    extract_numbered_heading_entries,
    extract_page_texts,
)


@dataclass
class ChapterData:
    chapter_title: str
    subtopics: list[dict[str, str]]


class TutorPipeline:
    def __init__(self) -> None:
        settings = get_settings()
        self.settings = settings
        self.scraper = NCERTScraper()
        self.embedder = Embedder()

    @staticmethod
    def _normalize_title(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", value.lower())

    def _unique_titles(self, titles: list[str]) -> list[str]:
        unique: list[str] = []
        seen: set[str] = set()
        for title in titles:
            normalized = self._normalize_title(title)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            unique.append(title)
        return unique

    def _unique_heading_titles(
        self,
        headings: list[tuple[int, str, float]] | list[tuple[int, str]],
        exclude: str | None = None,
    ) -> list[str]:
        titles = [item[1] for item in headings]
        counts = Counter(self._normalize_title(title) for title in titles if title)
        excluded = self._normalize_title(exclude) if exclude else ""
        
        # Filter: keep meaningful titles, remove obvious noise and excessive duplicates
        filtered = [
            title
            for title in titles
            if title
            and len(title) > 4
            and not title.isdigit()
            and not title.lower() in ('page', 'chapter', 'figure', 'table', 'continue')
            and self._normalize_title(title) != excluded
            and counts[self._normalize_title(title)] <= 2  # Allow up to 2 occurrences
        ]
        
        # Deduplicate: keep longest version of similar titles
        unique_map: dict[str, str] = {}
        for title in filtered:
            norm = self._normalize_title(title)
            existing = unique_map.get(norm, "")
            # Keep the longer/more complete title if it exists
            if not existing or len(title) > len(existing):
                unique_map[norm] = title
        
        # Return in order of first appearance from filtered list
        result = []
        seen_norms = set()
        for title in filtered:
            norm = self._normalize_title(title)
            if norm not in seen_norms:
                result.append(unique_map[norm])
                seen_norms.add(norm)
        
        return result

    def _structured_topic_context(
        self,
        pdf_path,
        chapter_title: str,
        topic_title: str,
    ) -> tuple[str, list[tuple[int, str]], list[tuple[int, str]]]:
        chapter = extract_chapter(pdf_path, chapter_title)
        topic_entries = extract_numbered_heading_entries(pdf_path, chapter.pages, depth=1)
        subtopic_entries = extract_numbered_heading_entries(pdf_path, chapter.pages, depth=2)
        if not topic_entries:
            topic_entries = [(page, title) for page, title, _ in extract_heading_lines(pdf_path, chapter.pages)]
        if not subtopic_entries:
            subtopic_entries = [(page, title) for page, title, _ in extract_heading_lines(pdf_path, chapter.pages)]

        selected_page = None
        selected_normalized = self._normalize_title(topic_title)
        for page_number, heading in topic_entries:
            normalized_heading = self._normalize_title(heading)
            if selected_normalized and (
                selected_normalized in normalized_heading or normalized_heading in selected_normalized
            ):
                selected_page = page_number
                break

        if selected_page is None:
            return "", topic_entries, subtopic_entries

        following_topic_pages = [
            page_number for page_number, _ in topic_entries if page_number > selected_page
        ]
        next_topic_page = min(following_topic_pages) if following_topic_pages else None
        page_end = next_topic_page - 1 if next_topic_page is not None else chapter.pages[-1]
        page_numbers = list(range(selected_page, page_end + 1))
        page_texts = extract_page_texts(pdf_path, page_numbers)
        context_text = "\n\n".join(text for _, text in page_texts if text).strip()
        return context_text, topic_entries, subtopic_entries

    def _find_heading_page(
        self,
        entries: list[tuple[int, str]],
        wanted_title: str,
    ) -> int | None:
        wanted_normalized = self._normalize_title(wanted_title)
        if not wanted_normalized:
            return None
        for page_number, heading in entries:
            normalized_heading = self._normalize_title(heading)
            if wanted_normalized in normalized_heading or normalized_heading in wanted_normalized:
                return page_number
        return None

    def _page_range_until_next_heading(
        self,
        entries: list[tuple[int, str]],
        start_page: int,
        fallback_end_page: int,
    ) -> list[int]:
        following_pages = [page_number for page_number, _ in entries if page_number > start_page]
        end_page = min(following_pages) - 1 if following_pages else fallback_end_page
        return list(range(start_page, max(start_page, end_page) + 1))

    def _page_chunks(
        self,
        pdf_path,
        pages: list[int],
        chapter_title: str,
        topic_title: str,
        subtopic_title: str,
    ) -> list[RetrievedChunk]:
        page_texts = extract_page_texts(pdf_path, pages)
        chunks: list[RetrievedChunk] = []
        for page_number, text in page_texts:
            if not text.strip():
                continue
            chunks.append(
                RetrievedChunk(
                    text=text,
                    score=1.0,
                    metadata={
                        "page": page_number,
                        "chapter": chapter_title,
                        "topic": topic_title,
                        "subtopic": subtopic_title,
                    },
                )
            )
        return chunks

    async def load_chapter(
        self, class_name: str, subject: str, book_title: str, chapter_title: str
    ) -> ChapterData:
        chapter_text = await self.get_chapter_context(
            class_name, subject, book_title, chapter_title
        )
        title_for_prompt = chapter_title
        if self.settings.use_llm_subtopics:
            try:
                subtopics = await extract_subtopics_llm(title_for_prompt, chapter_text)
            except Exception:
                subtopics = []
            if not subtopics:
                subtopics = extract_subtopics(chapter_text)
        else:
            subtopics = extract_subtopics(chapter_text)
        return ChapterData(chapter_title=chapter_title, subtopics=subtopics)

    async def list_chapters(self, class_name: str, subject: str, book_title: str) -> list[str]:
        pdf_path = await self.scraper.download_pdf(class_name, subject, book_title)
        chapters = extract_chapters(pdf_path)
        titles = [chapter.title for chapter in chapters]
        return titles

    async def list_topics(
        self,
        class_name: str,
        subject: str,
        book_title: str,
        chapter_title: str,
    ) -> list[str]:
        pdf_path = await self.scraper.download_pdf(class_name, subject, book_title)
        chapter = extract_chapter(pdf_path, chapter_title)
        entries = extract_numbered_heading_entries(pdf_path, chapter.pages, depth=1)
        if not entries:
            entries = [
                (page_number, title)
                for page_number, title, _ in extract_heading_lines(pdf_path, chapter.pages)
                if self._normalize_title(title) != self._normalize_title(chapter.title)
            ]
        settings = self.settings
        titles = [title for _, title in entries]
        # Return full list if configured, otherwise keep unique filtered behavior
        if settings.full_headings_list:
            # filter out empty and exact-chapter-title matches, preserve order
            return [t for t in titles if t and self._normalize_title(t) != self._normalize_title(chapter.title)]
        if len(entries) > 1:
            return self._unique_heading_titles(entries, exclude=chapter.title)
        return self._unique_titles(titles)

    async def list_subtopics(
        self,
        class_name: str,
        subject: str,
        book_title: str,
        chapter_title: str,
        topic_title: str,
    ) -> list[str]:
        pdf_path = await self.scraper.download_pdf(class_name, subject, book_title)
        structured_context, topic_entries, subtopic_entries = self._structured_topic_context(
            pdf_path, chapter_title, topic_title
        )
        selected_page = self._find_heading_page(topic_entries, topic_title)
        if selected_page is None:
            return []

        chapter = extract_chapter(pdf_path, chapter_title)
        page_end = self._page_range_until_next_heading(
            topic_entries, selected_page, chapter.pages[-1]
        )[-1]
        titles = [
            heading
            for page_number, heading in subtopic_entries
            if selected_page <= page_number <= page_end
        ]
        settings = self.settings
        if settings.full_headings_list:
            filtered = [t for t in titles if t and self._normalize_title(t) != self._normalize_title(topic_title)]
            return filtered if filtered else [topic_title]
        unique_titles = self._unique_heading_titles(
            [(0, title) for title in titles], exclude=topic_title
        )
        if unique_titles:
            return unique_titles
        return [topic_title]

    async def get_chapter_context(
        self, class_name: str, subject: str, book_title: str, chapter_title: str
    ) -> str:
        pdf_path = await self.scraper.download_pdf(class_name, subject, book_title)
        chapter_text = ""
        try:
            chapter_text = extract_chapter(pdf_path, chapter_title).content
        except Exception:
            chapter_text = ""

        try:
            store = await self.build_book_index(class_name, subject, book_title)
            context_text = await self._chapter_context(
                chapter_title, store, self.settings.retrieval_candidate_k
            )
            if context_text.strip():
                return context_text
        except Exception:
            pass

        if chapter_text.strip():
            return chapter_text
        raise ValueError("Chapter not found")

    async def get_topic_context(
        self,
        class_name: str,
        subject: str,
        book_title: str,
        chapter_title: str,
        topic_title: str,
    ) -> str:
        pdf_path = await self.scraper.download_pdf(class_name, subject, book_title)
        structured_context, topic_entries, _ = self._structured_topic_context(
            pdf_path, chapter_title, topic_title
        )
        if structured_context:
            return structured_context
        selected_page = self._find_heading_page(topic_entries, topic_title)
        if selected_page is None:
            raise ValueError("Topic not found in book")

        chapter = extract_chapter(pdf_path, chapter_title)
        pages = self._page_range_until_next_heading(topic_entries, selected_page, chapter.pages[-1])
        page_texts = extract_page_texts(pdf_path, pages)
        context_text = "\n\n".join(text for _, text in page_texts if text).strip()
        if context_text:
            return context_text
        raise ValueError("Topic not found in book")

    async def get_subtopic_chunks(
        self,
        class_name: str,
        subject: str,
        book_title: str,
        chapter_title: str,
        topic_title: str,
        subtopic_title: str,
    ) -> list[RetrievedChunk]:
        pdf_path = await self.scraper.download_pdf(class_name, subject, book_title)
        chapter = extract_chapter(pdf_path, chapter_title)
        topic_entries = extract_numbered_heading_entries(pdf_path, chapter.pages, depth=1)
        if not topic_entries:
            topic_entries = [
                (page_number, title)
                for page_number, title, _ in extract_heading_lines(pdf_path, chapter.pages)
                if self._normalize_title(title) != self._normalize_title(chapter.title)
            ]

        topic_page = self._find_heading_page(topic_entries, topic_title)
        if topic_page is None:
            raise ValueError("Topic not found in book")

        subtopic_entries = extract_numbered_heading_entries(pdf_path, chapter.pages, depth=2)
        if not subtopic_entries:
            subtopic_entries = [
                (page_number, title)
                for page_number, title, _ in extract_heading_lines(pdf_path, chapter.pages)
            ]

        selected_page = self._find_heading_page(subtopic_entries, subtopic_title)
        if selected_page is None:
            if self._normalize_title(subtopic_title) == self._normalize_title(topic_title):
                selected_page = topic_page
            else:
                raise ValueError("Subtopic not found in book")

        chapter_end = chapter.pages[-1]
        pages = self._page_range_until_next_heading(subtopic_entries, selected_page, chapter_end)
        chunks = self._page_chunks(pdf_path, pages, chapter.title, topic_title, subtopic_title)
        if not chunks:
            raise ValueError("Subtopic not found in book")
        return chunks

    async def build_book_index(
        self, class_name: str, subject: str, book_title: str
    ) -> VectorStore:
        def safe_slug(value: str) -> str:
            cleaned = re.sub(r"[^a-z0-9]+", "_", value.lower())
            return cleaned.strip("_")

        index_name = safe_slug(f"{class_name}_{subject}_{book_title}_full")
        index_path = self.settings.index_dir / index_name
        if index_path.with_suffix(".faiss").exists():
            return VectorStore.load(index_path)

        pdf_path = await self.scraper.download_pdf(class_name, subject, book_title)
        chapters = extract_chapters(pdf_path)
        if not chapters:
            raise ValueError("No content found in book")
        chunks = []
        for chapter in chapters:
            page_texts = extract_page_texts(pdf_path, chapter.pages)
            chunks.extend(
                chunk_text(
                    page_texts,
                    chapter=chapter.title,
                    subtopic=None,
                    chunk_size=self.settings.chunk_size,
                    overlap=self.settings.chunk_overlap,
                )
            )
        texts = [chunk.text for chunk in chunks]
        vectors = await self._embed_batches(texts)
        store = VectorStore(vectors.shape[1])
        metadatas = []
        for chunk in chunks:
            meta = dict(chunk.metadata)
            meta["text"] = chunk.text
            metadatas.append(meta)
        store.add(vectors, metadatas)
        store.save(index_path)
        return store

    async def _embed_batches(self, texts: list[str]):
        batch_size = max(1, self.settings.embedding_batch_size)
        vectors = []
        for idx in range(0, len(texts), batch_size):
            batch = texts[idx : idx + batch_size]
            vectors.append(await self.embedder.embed(batch))
        if not vectors:
            return self.embedder.embed([""])
        return np.vstack(vectors)

    async def _chapter_context(
        self, chapter_title: str, store: VectorStore, candidate_k: int
    ) -> str:
        retriever = Retriever(store, self.embedder)
        chunks = await retriever.retrieve(
            chapter_title,
            top_k=self.settings.retrieval_top_k,
            candidate_k=candidate_k,
            chapter_title=chapter_title,
        )
        return "\n\n".join(chunk.text for chunk in chunks)

    def _heuristic_chapters(self, text: str) -> list[str]:
        matches = re.findall(r"chapter\s+\d+\s*[:\-]?\s*[^\n\.]{3,80}", text, re.IGNORECASE)
        cleaned = []
        for match in matches:
            title = " ".join(match.split())
            if title.lower() not in (t.lower() for t in cleaned):
                cleaned.append(title)
        return cleaned

    async def retrieve(
        self, query: str, store: VectorStore, chapter_title: str | None = None
    ) -> list[RetrievedChunk]:
        retriever = Retriever(store, self.embedder)
        try:
            return await retriever.retrieve(
                query,
                self.settings.retrieval_top_k,
                self.settings.retrieval_candidate_k,
                chapter_title=chapter_title,
            )
        except Exception:
            return []
