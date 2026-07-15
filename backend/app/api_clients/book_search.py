"""여러 도서 API를 병렬 조회하고 중복을 합치는 통합 검색."""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Callable

from app.api_clients.aladin_books import AladinBooksClient
from app.api_clients.google_books import GoogleBooksClient
from app.api_clients.kakao_books import KakaoBooksClient
from app.api_clients.naver_books import NaverBooksClient


@dataclass(frozen=True)
class BookSearchResult:
    books: list[dict]
    successful_providers: list[str]
    failed_providers: list[str]


def _provider_searchers() -> list[tuple[str, Callable[[str, int], list[dict]]]]:
    return [
        ("네이버", NaverBooksClient().search_book),
        ("알라딘", AladinBooksClient().search_book),
        ("Google Books", GoogleBooksClient().search_book),
        ("카카오", KakaoBooksClient().search_book),
    ]


def _dedupe_key(book: dict) -> str:
    isbn = re.sub(r"[^0-9X]", "", str(book.get("isbn") or "").upper())
    if len(isbn) in (10, 13):
        return f"isbn:{isbn}"
    title = re.sub(r"\W", "", str(book.get("title") or "").casefold())
    author = re.sub(r"\W", "", str(book.get("author") or "").casefold())
    return f"title:{title}:{author}"


def _normalize_book(book: dict, provider: str) -> dict:
    source = str(book.get("source") or provider)
    return {
        "title": book.get("title"),
        "author": book.get("author"),
        "publisher": book.get("publisher"),
        "pub_year": book.get("pub_year"),
        "isbn": book.get("isbn"),
        "thumbnail_url": book.get("thumbnail_url"),
        "description": book.get("description"),
        "link": book.get("link"),
        "genre": book.get("genre"),
        "sources": [source],
    }


def _merge_book(existing: dict, incoming: dict) -> None:
    for field in (
        "author",
        "publisher",
        "pub_year",
        "isbn",
        "thumbnail_url",
        "description",
        "link",
        "genre",
    ):
        if not existing.get(field) and incoming.get(field):
            existing[field] = incoming[field]
    for source in incoming.get("sources", []):
        if source not in existing["sources"]:
            existing["sources"].append(source)


def search_books(query: str, size_per_provider: int = 5, limit: int = 8) -> BookSearchResult:
    providers = _provider_searchers()
    provider_results: dict[str, list[dict]] = {}
    failed_providers: list[str] = []

    with ThreadPoolExecutor(max_workers=len(providers)) as executor:
        futures = {
            executor.submit(searcher, query, size_per_provider): provider
            for provider, searcher in providers
        }
        for future in as_completed(futures):
            provider = futures[future]
            try:
                provider_results[provider] = future.result()
            except Exception:
                failed_providers.append(provider)

    combined: list[dict] = []
    by_key: dict[str, dict] = {}
    max_provider_results = max((len(items) for items in provider_results.values()), default=0)

    # 각 제공자의 상위 결과를 번갈아 넣어 한 서비스의 결과만 채워지지 않게 한다.
    for index in range(max_provider_results):
        for provider, _searcher in providers:
            items = provider_results.get(provider, [])
            if index >= len(items):
                continue
            normalized = _normalize_book(items[index], provider)
            if not normalized.get("title"):
                continue
            key = _dedupe_key(normalized)
            if key in by_key:
                _merge_book(by_key[key], normalized)
                continue
            by_key[key] = normalized
            combined.append(normalized)

    successful = [provider for provider, _ in providers if provider in provider_results]
    failed = [provider for provider, _ in providers if provider in failed_providers]
    return BookSearchResult(
        books=combined[: max(1, limit)],
        successful_providers=successful,
        failed_providers=failed,
    )
