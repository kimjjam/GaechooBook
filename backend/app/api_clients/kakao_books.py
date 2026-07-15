"""카카오 도서 검색 API에서 시드용 도서 데이터를 가져온다.

카카오 도서 검색 응답에는 장르/카테고리 필드가 없어서, 검색에 사용한
쿼리어(예: "소설")를 그대로 genre 값으로 태깅한다.
"""
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

_BASE_URL = "https://dapi.kakao.com/v3/search/book"

_SEED_QUERIES = ["소설", "에세이", "자기계발", "인문학", "과학"]


class KakaoBooksClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("KAKAO_BOOKS_API_KEY", "")

    def search_book(self, query: str, size: int = 10) -> list[dict]:
        resp = httpx.get(
            _BASE_URL,
            params={"query": query, "size": size, "sort": "accuracy"},
            headers={"Authorization": f"KakaoAK {self.api_key}"},
            timeout=10,
        )
        resp.raise_for_status()
        documents = resp.json().get("documents", [])
        results = []
        for doc in documents:
            datetime_str = doc.get("datetime") or ""
            pub_year = int(datetime_str[:4]) if len(datetime_str) >= 4 else None
            authors = doc.get("authors") or []
            results.append(
                {
                    "title": doc.get("title"),
                    "author": ", ".join(authors) if authors else None,
                    "genre": query,
                    "pub_year": pub_year,
                }
            )
        return results

    def collect_seed_books(self) -> list[dict]:
        combined: list[dict] = []
        seen_titles: set[str] = set()
        for query in _SEED_QUERIES:
            for book in self.search_book(query, size=10):
                if not book["title"] or book["title"] in seen_titles:
                    continue
                seen_titles.add(book["title"])
                combined.append(book)
        return combined
