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


def test_discovery_passes_structured_filters_to_tmdb(monkeypatch):
    client = TMDBClient(api_key="test")
    calls = []
    monkeypatch.setattr(
        client,
        "_get",
        lambda _path, params: calls.append(params) or {"results": []},
    )

    client.discover_for_genres(
        ["로맨스"],
        filters={
            "vote_average.gte": 7.0,
            "primary_release_date.gte": "2020-01-01",
            "with_runtime.lte": 120,
        },
    )

    assert all(call["vote_average.gte"] == 7.0 for call in calls)
    assert all(call["with_runtime.lte"] == 120 for call in calls)
    assert all(call["with_genres"] == "10749" for call in calls)


def test_similar_movie_recommendations_use_search_result(monkeypatch):
    client = TMDBClient(api_key="test")
    calls = []

    def fake_get(path, params):
        calls.append((path, params))
        if path == "/search/movie":
            return {"results": [{"id": 597, "title": "타이타닉"}]}
        return {
            "results": [
                {
                    "id": 1,
                    "title": "비슷한 영화",
                    "genre_ids": [10749],
                    "release_date": "2022-01-01",
                    "vote_average": 7.5,
                },
                {
                    "id": 2,
                    "title": "평점 미달",
                    "genre_ids": [10749],
                    "release_date": "2022-01-01",
                    "vote_average": 6.5,
                },
            ]
        }

    monkeypatch.setattr(client, "_get", fake_get)
    movies = client.recommend_similar("타이타닉", filters={"vote_average.gte": 7.0})

    assert [movie["id"] for movie in movies] == [1]
    assert calls[0][0] == "/search/movie"
    assert calls[1][0] == "/movie/597/recommendations"
