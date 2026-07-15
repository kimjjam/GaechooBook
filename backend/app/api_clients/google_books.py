"""Google Books Volumes API 클라이언트."""

import os

import httpx
from dotenv import load_dotenv

from app.api_clients.book_common import clean_text, normalize_isbn, publication_year

load_dotenv()

_BASE_URL = "https://www.googleapis.com/books/v1/volumes"


class GoogleBooksClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("GOOGLE_BOOKS_API_KEY", "")

    def search_book(self, query: str, size: int = 10) -> list[dict]:
        params: dict[str, str | int] = {
            "q": query,
            "maxResults": min(max(size, 1), 40),
            "orderBy": "relevance",
            "langRestrict": "ko",
        }
        if self.api_key:
            params["key"] = self.api_key

        response = httpx.get(_BASE_URL, params=params, timeout=10)
        response.raise_for_status()

        books = []
        for item in response.json().get("items", []):
            info = item.get("volumeInfo") or {}
            identifiers = info.get("industryIdentifiers") or []
            isbn_values = [entry.get("identifier") for entry in identifiers]
            isbn = next(
                (normalize_isbn(value) for value in isbn_values if normalize_isbn(value)),
                None,
            )
            image_links = info.get("imageLinks") or {}
            authors = info.get("authors") or []
            categories = info.get("categories") or []
            books.append(
                {
                    "title": clean_text(info.get("title")),
                    "author": clean_text(", ".join(authors)) if authors else None,
                    "publisher": clean_text(info.get("publisher")),
                    "pub_year": publication_year(info.get("publishedDate")),
                    "isbn": isbn,
                    "thumbnail_url": image_links.get("thumbnail") or image_links.get("smallThumbnail"),
                    "description": clean_text(info.get("description")),
                    "link": info.get("infoLink") or item.get("selfLink"),
                    "genre": clean_text(", ".join(categories)) if categories else query,
                    "source": "Google Books",
                }
            )
        return [book for book in books if book["title"]]
