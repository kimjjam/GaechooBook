"""네이버 책 검색 API 클라이언트.

네이버 책 검색 API는 2026-07-31 종료 예정이므로 통합 검색에서는
실패해도 다른 제공자의 결과를 계속 사용한다.
"""

import os

import httpx
from dotenv import load_dotenv

from app.api_clients.book_common import clean_text, normalize_isbn, publication_year

load_dotenv()

_BASE_URL = "https://openapi.naver.com/v1/search/book.json"


class NaverBooksClient:
    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
    ):
        self.client_id = client_id or os.getenv("NAVER_CLIENT_ID", "")
        self.client_secret = client_secret or os.getenv("NAVER_CLIENT_SECRET", "")

    def search_book(self, query: str, size: int = 10) -> list[dict]:
        if not self.client_id or not self.client_secret:
            raise RuntimeError("네이버 검색 API 인증 정보가 설정되지 않았습니다.")

        response = httpx.get(
            _BASE_URL,
            params={"query": query, "display": min(max(size, 1), 100), "sort": "sim"},
            headers={
                "X-Naver-Client-Id": self.client_id,
                "X-Naver-Client-Secret": self.client_secret,
            },
            timeout=10,
        )
        response.raise_for_status()

        books = []
        for item in response.json().get("items", []):
            books.append(
                {
                    "title": clean_text(item.get("title")),
                    "author": clean_text(item.get("author")),
                    "publisher": clean_text(item.get("publisher")),
                    "pub_year": publication_year(item.get("pubdate")),
                    "isbn": normalize_isbn(item.get("isbn")),
                    "thumbnail_url": item.get("image") or None,
                    "description": clean_text(item.get("description")),
                    "link": item.get("link") or None,
                    "genre": query,
                    "source": "네이버",
                }
            )
        return [book for book in books if book["title"]]
