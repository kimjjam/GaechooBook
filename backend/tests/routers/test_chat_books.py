from app.api_clients.book_search import BookSearchResult
from app.routers import chat


def test_book_recommendation_uses_live_integrated_search(monkeypatch):
    captured = {}

    def fake_search(query: str, size_per_provider: int, limit: int) -> BookSearchResult:
        captured.update(query=query, size=size_per_provider, limit=limit)
        return BookSearchResult(
            books=[
                {
                    "title": "해리 포터와 마법사의 돌",
                    "author": "J. K. 롤링",
                    "pub_year": 1999,
                    "sources": ["네이버", "알라딘"],
                }
            ],
            successful_providers=["네이버", "알라딘", "Google Books"],
            failed_providers=["카카오"],
        )

    monkeypatch.setattr(chat, "search_books", fake_search)

    response = chat._handle_recommend("해리포터 책 검색해줘", "visitor")

    assert captured == {"query": "해리포터", "size": 5, "limit": 5}
    assert response.reply == "취향을 반영해 책 1권을 골랐어요. 카드를 눌러 간단히 살펴보세요."
    assert response.data["failed_providers"] == ["카카오"]


def test_preference_search_relaxes_query_and_fills_five_cards(monkeypatch):
    calls = []

    def fake_search(query: str, size_per_provider: int, limit: int) -> BookSearchResult:
        calls.append(query)
        count = 1 if "," in query else 5
        return BookSearchResult(
            books=[
                {
                    "title": f"과학책 {index}",
                    "author": "과학 저자",
                    "isbn": f"97812345678{index:02d}",
                    "sources": ["Google Books"],
                }
                for index in range(count)
            ],
            successful_providers=["Google Books"],
            failed_providers=[],
        )

    monkeypatch.setattr(chat, "search_books", fake_search)

    response = chat._handle_recommend(
        "책 추천: 과학기술, 새로운 지식, 가볍고 편하게, 실용적인 지식과 탐구",
        "visitor",
    )

    assert calls == [
        "과학기술, 새로운 지식, 가볍고 편하게, 실용적인 지식과 탐구",
        "과학기술",
    ]
    assert len(response.data["books"]) == 5
    assert response.reply.startswith("취향을 반영해 책 5권")


def test_provider_failures_are_not_exposed_when_no_books_are_found(monkeypatch):
    monkeypatch.setattr(
        chat,
        "search_books",
        lambda *_args, **_kwargs: BookSearchResult(
            books=[], successful_providers=[], failed_providers=["네이버", "카카오"],
        ),
    )

    response = chat._handle_recommend("찾기 어려운 책 추천해줘", "visitor")

    assert response.data["books"] == []
    assert "네이버" not in response.reply
    assert "카카오" not in response.reply
