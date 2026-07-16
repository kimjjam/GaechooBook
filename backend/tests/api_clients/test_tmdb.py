from app.api_clients.tmdb import TMDBClient


def _movie(movie_id: int) -> dict:
    return {
        "id": movie_id,
        "title": f"Movie {movie_id}",
        "genre_ids": [],
        "release_date": "2024-01-01",
    }


def test_discovery_combines_sort_modes_and_removes_duplicates(monkeypatch):
    client = TMDBClient(api_key="test")
    calls = []

    def fake_get(_path, params):
        calls.append(params)
        index = len(calls)
        return {"results": [_movie(1), _movie(index + 1)]}

    monkeypatch.setattr(client, "_get", fake_get)

    results = client.discover_for_genres([], count=10, diversity_seed="user-7")

    assert len(calls) == 4
    assert {call["sort_by"] for call in calls} == {
        "popularity.desc",
        "vote_average.desc",
        "primary_release_date.desc",
    }
    assert [movie["id"] for movie in results] == [1, 2, 3, 4, 5]


def test_discovery_seed_changes_candidate_pages(monkeypatch):
    client = TMDBClient(api_key="test")
    pages_by_seed = []

    def capture_pages(seed):
        calls = []
        monkeypatch.setattr(
            client,
            "_get",
            lambda _path, params: calls.append(params) or {"results": []},
        )
        client.discover_for_genres([], count=80, diversity_seed=seed)
        pages_by_seed.append(
            sorted(
                (call["sort_by"], call["vote_count.gte"], call["page"])
                for call in calls
            )
        )

    capture_pages("user-7")
    capture_pages("user-8")

    assert pages_by_seed[0] != pages_by_seed[1]
