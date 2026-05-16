from __future__ import annotations

import io
import json
import re
import zipfile
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse, parse_qs

import httpx
import fitz

from backend.config.settings import get_settings
from backend.utils.security import is_safe_url


class NCERTScraper:
    def __init__(self, catalog_path: Path | None = None) -> None:
        settings = get_settings()
        self.catalog_path = catalog_path or settings.ncert_catalog_path
        self.cache_dir = settings.pdf_cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/pdf;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://ncert.nic.in/",
        }

    async def _get(self, url: str) -> httpx.Response:
        async with httpx.AsyncClient(timeout=300.0, follow_redirects=True) as client:
            try:
                return await client.get(url, headers=self.headers)
            except httpx.RequestError:
                return await client.get(url, headers=self.headers)

    def _load_catalog(self) -> dict[str, Any]:
        with self.catalog_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    async def list_books(self, class_name: str, subject: str) -> list[str]:
        catalog = self._load_catalog()
        key = f"class_{class_name.lower()}"
        subject_key = subject.lower().replace(" ", "_")
        entries = catalog.get(key, {}).get(subject_key, [])
        if not entries:
            raise ValueError("No books found in catalog")
        return [entry["title"] for entry in entries]

    async def get_book_url(self, class_name: str, subject: str, book_title: str) -> str:
        catalog = self._load_catalog()
        key = f"class_{class_name.lower()}"
        subject_key = subject.lower().replace(" ", "_")
        entries = catalog.get(key, {}).get(subject_key, [])
        if not entries:
            raise ValueError("Book URL not found in catalog")
        match = next((e for e in entries if e["title"].lower() == book_title.lower()), None)
        if not match:
            raise ValueError("Book title not found in catalog")
        url = match.get("url")
        if not url or not is_safe_url(url):
            raise ValueError("Book URL not found in catalog")
        return url

    async def _resolve_textbook_download(self, url: str) -> str:
        try:
            response = await self._get(url)
            response.raise_for_status()
        except httpx.RequestError as exc:
            raise ValueError(f"Failed to reach NCERT page: {url}") from exc
        except httpx.HTTPStatusError as exc:
            raise ValueError(
                f"NCERT page returned {exc.response.status_code} for {url}"
            ) from exc
        html = response.text

        anchors = re.findall(
            r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
            html,
            flags=re.IGNORECASE | re.DOTALL,
        )
        candidate = None
        for href, text in anchors:
            cleaned_text = re.sub(r"<[^>]+>", "", text).strip().lower()
            if "download complete book" in cleaned_text or "complete book" in cleaned_text:
                candidate = href
                break

        if not candidate:
            hrefs = re.findall(r'href=["\']([^"\']+)["\']', html, flags=re.IGNORECASE)
            zip_links = [
                h for h in hrefs if "textbook/pdf/" in h and h.lower().endswith(".zip")
            ]
            pdf_links = [
                h for h in hrefs if "textbook/pdf/" in h and h.lower().endswith(".pdf")
            ]
            if zip_links or pdf_links:
                candidate = (zip_links + pdf_links)[-1]

        if not candidate:
            file_links = re.findall(
                r"textbook/pdf/[^\"'\s>]+\.(?:pdf|zip)",
                html,
                flags=re.IGNORECASE,
            )
            if file_links:
                candidate = file_links[-1]

        if candidate and not candidate.lower().endswith((".pdf", ".zip")):
            candidate = None
        if not candidate:
            parsed = urlparse(url)
            keys = list(parse_qs(parsed.query).keys())
            if keys:
                candidate = f"textbook/pdf/{keys[0]}dd.zip"
            else:
                raise ValueError("Download link not found on NCERT page")
        resolved = urljoin("https://ncert.nic.in/", candidate)
        if not is_safe_url(resolved):
            raise ValueError("Resolved NCERT URL is not safe")
        return resolved

    def _looks_incomplete_pdf(self, pdf_path: Path) -> bool:
        if pdf_path.stat().st_size < 200_000:
            return True
        try:
            with fitz.open(str(pdf_path)) as doc:
                return doc.page_count < 10
        except Exception:
            return True

    def _merge_pdfs_from_zip(self, archive: zipfile.ZipFile, target: Path) -> None:
        pdf_names = [n for n in archive.namelist() if n.lower().endswith(".pdf")]
        if not pdf_names:
            raise ValueError("No PDF found in NCERT archive")

        def sort_key(name: str) -> tuple[int, str]:
            match = re.search(r"(\d+)", name)
            return (int(match.group(1)) if match else 10_000, name.lower())

        pdf_names.sort(key=sort_key)
        merged = fitz.open()
        for name in pdf_names:
            with archive.open(name) as pdf_file:
                data = pdf_file.read()
            try:
                doc = fitz.open(stream=data, filetype="pdf")
            except Exception:
                continue
            merged.insert_pdf(doc)
            doc.close()

        if merged.page_count == 0:
            merged.close()
            raise ValueError("No usable PDFs found in NCERT archive")
        merged.save(str(target))
        merged.close()

    async def download_pdf(self, class_name: str, subject: str, book_title: str) -> Path:
        safe_book = re.sub(r"[^a-z0-9]+", "_", book_title.lower()).strip("_")
        filename = f"{class_name}_{subject.lower().replace(' ', '_')}_{safe_book}.pdf"
        target = self.cache_dir / filename
        if target.exists():
            if self._looks_incomplete_pdf(target):
                raise ValueError(
                    "Cached PDF looks incomplete. Replace it with the full book or delete it to re-download."
                )
            return target

        url = await self.get_book_url(class_name, subject, book_title)
        if "textbook.php" in url:
            url = await self._resolve_textbook_download(url)

        try:
            response = await self._get(url)
            response.raise_for_status()
        except httpx.RequestError as exc:
            raise ValueError(f"Failed to download book from {url}") from exc
        except httpx.HTTPStatusError as exc:
            raise ValueError(
                f"Book download returned {exc.response.status_code} for {url}"
            ) from exc

        if url.lower().endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
                self._merge_pdfs_from_zip(archive, target)
        else:
            target.write_bytes(response.content)

        if not target.exists():
            raise ValueError(f"Failed to create cached PDF at {target}")
        return target
