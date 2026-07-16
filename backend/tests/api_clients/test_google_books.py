import httpx

from app.api_clients.google_books import GoogleBooksClient


def test_google_books_retries_without_restricted_api_key(monkeypatch):
    calls = []

    def fake_get(url, params, timeout):
        calls.append(dict(params))
        status = 400 if "key" in params else 200
        return httpx.Response(
            status,
            request=httpx.Request("GET", url),
            json={"items": []} if status == 200 else {"error": "restricted key"},
        )

    monkeypatch.setattr(httpx, "get", fake_get)

    result = GoogleBooksClient(api_key="restricted-key").search_book("과학", size=5)

    assert result == []
    assert calls[0]["key"] == "restricted-key"
    assert "key" not in calls[1]
