from app.api_clients import book_search


def test_search_books_merges_duplicate_isbn(monkeypatch):
    def naver_search(_query: str, _size: int) -> list[dict]:
        return [
            {
                "title": "테스트 책",
                "author": "홍길동",
                "isbn": "9781234567890",
                "source": "네이버",
            }
        ]

    def aladin_search(_query: str, _size: int) -> list[dict]:
        return [
            {
                "title": "테스트 책 (개정판)",
                "publisher": "테스트 출판사",
                "isbn": "978-1-234-56789-0",
                "source": "알라딘",
            }
        ]

    monkeypatch.setattr(
        book_search,
        "_provider_searchers",
        lambda: [("네이버", naver_search), ("알라딘", aladin_search)],
    )

    result = book_search.search_books("테스트", size_per_provider=5, limit=5)

    assert len(result.books) == 1
    assert result.books[0]["publisher"] == "테스트 출판사"
    assert result.books[0]["sources"] == ["네이버", "알라딘"]
    assert result.successful_providers == ["네이버", "알라딘"]
    assert result.failed_providers == []


def test_search_books_keeps_results_when_one_provider_fails(monkeypatch):
    def failed_search(_query: str, _size: int) -> list[dict]:
        raise RuntimeError("provider unavailable")

    def google_search(_query: str, _size: int) -> list[dict]:
        return [{"title": "살아남은 결과", "source": "Google Books"}]

    monkeypatch.setattr(
        book_search,
        "_provider_searchers",
        lambda: [("네이버", failed_search), ("Google Books", google_search)],
    )

    result = book_search.search_books("테스트")

    assert [book["title"] for book in result.books] == ["살아남은 결과"]
    assert result.successful_providers == ["Google Books"]
    assert result.failed_providers == ["네이버"]


def test_search_books_interleaves_multiple_provider_results(monkeypatch):
    def provider(name: str):
        def search(_query: str, _size: int) -> list[dict]:
            return [
                {"title": f"{name} 추천 {index}", "source": name}
                for index in range(2)
            ]

        return search

    monkeypatch.setattr(
        book_search,
        "_provider_searchers",
        lambda: [
            ("네이버", provider("네이버")),
            ("알라딘", provider("알라딘")),
            ("Google Books", provider("Google Books")),
            ("카카오", provider("카카오")),
        ],
    )

    result = book_search.search_books("과학", size_per_provider=5, limit=5)

    assert [book["sources"][0] for book in result.books] == [
        "네이버",
        "알라딘",
        "Google Books",
        "카카오",
        "네이버",
    ]
