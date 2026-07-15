from app.api_clients.tmdb import TMDBClient


def test_movie_details_prefers_official_youtube_trailer(monkeypatch):
    client = TMDBClient(api_key="test-key")
    monkeypatch.setattr(
        client,
        "_get",
        lambda _path, _params: {
            "id": 42,
            "title": "테스트 영화",
            "overview": "상세 줄거리",
            "release_date": "2026-07-16",
            "runtime": 123,
            "vote_average": 8.4,
            "genres": [{"name": "SF"}],
            "poster_path": "/poster.jpg",
            "backdrop_path": "/backdrop.jpg",
            "videos": {
                "results": [
                    {"site": "YouTube", "type": "Trailer", "official": False, "key": "fan"},
                    {"site": "YouTube", "type": "Trailer", "official": True, "key": "official"},
                ]
            },
        },
    )

    detail = client.get_movie_details(42)

    assert detail["release_year"] == 2026
    assert detail["genres"] == ["SF"]
    assert detail["trailer_url"] == "https://www.youtube.com/embed/official"
