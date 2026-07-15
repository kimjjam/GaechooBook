"""알라딘 TTB 도서 검색 API 클라이언트."""

import os

import httpx
from dotenv import load_dotenv

from app.api_clients.book_common import clean_text, normalize_isbn, publication_year

load_dotenv()

_BASE_URL = "https://www.aladin.co.kr/ttb/api/ItemSearch.aspx"


class AladinBooksClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("ALADIN_TTB_KEY", "")

    def search_book(self, query: str, size: int = 10) -> list[dict]:
        if not self.api_key:
            raise RuntimeError("알라딘 TTB 키가 설정되지 않았습니다.")

        response = httpx.get(
            _BASE_URL,
            params={
                "ttbkey": self.api_key,
                "Query": query,
                "QueryType": "Keyword",
                "MaxResults": min(max(size, 1), 50),
                "start": 1,
                "SearchTarget": "Book",
                "output": "js",
                "Version": "20131101",
                "Cover": "Big",
            },
            timeout=10,
        )
        response.raise_for_status()

        books = []
        for item in response.json().get("item", []):
            books.append(
                {
                    "title": clean_text(item.get("title")),
                    "author": clean_text(item.get("author")),
                    "publisher": clean_text(item.get("publisher")),
                    "pub_year": publication_year(item.get("pubDate")),
                    "isbn": normalize_isbn(item.get("isbn13") or item.get("isbn")),
                    "thumbnail_url": item.get("cover") or None,
                    "description": clean_text(item.get("description")),
                    "link": item.get("link") or None,
                    "genre": clean_text(item.get("categoryName")) or query,
                    "source": "알라딘",
                }
            )
        return [book for book in books if book["title"]]
