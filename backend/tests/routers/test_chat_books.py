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

    assert captured == {"query": "해리포터", "size": 5, "limit": 6}
    assert "해리 포터와 마법사의 돌" in response.reply
    assert response.data["failed_providers"] == ["카카오"]
