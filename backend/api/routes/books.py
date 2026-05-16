from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.api.schemas import BookRequest
from backend.scraping.ncert_scraper import NCERTScraper

router = APIRouter(tags=["books"])


@router.get("/books")
async def list_all_books() -> dict[str, list[dict]]:
    """Get all available books grouped by class and subject"""
    scraper = NCERTScraper()
    try:
        books_list = []
        for class_name in ["6", "7", "8", "9", "10", "11", "12"]:
            for subject in ["science", "math", "english", "social"]:
                try:
                    books = await scraper.list_books(class_name, subject)
                    for book in books:
                        books_list.append({
                            "class": class_name,
                            "subject": subject,
                            "book": book
                        })
                except:
                    pass
        return {"books": books_list}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/books")
async def list_books(payload: BookRequest) -> dict[str, list[str]]:
    scraper = NCERTScraper()
    try:
        books = await scraper.list_books(payload.class_name, payload.subject)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"books": books}
