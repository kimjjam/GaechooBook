from app.core.scoring.recommendation import rank_movies


def test_preferred_genre_ranks_first():
    movies = [
        {"id": 1, "title": "액션 영화", "genres": ["액션"], "rating": 7.5, "popularity": 80},
        {"id": 2, "title": "공포 영화", "genres": ["공포"], "rating": 9.0, "popularity": 100},
    ]
    ranked = rank_movies(movies, {"액션": 1.0}, {}, set(), limit=2)
    assert ranked[0]["id"] == 1


def test_seen_movies_are_excluded():
    movies = [{"id": 1, "title": "이미 본 영화", "genres": ["액션"], "rating": 8, "popularity": 80}]
    assert rank_movies(movies, {"액션": 1.0}, {}, {1}) == []


def test_duplicate_movie_ids_are_returned_once():
    movies = [
        {"id": 1, "title": "오디세이", "genres": ["액션"], "rating": 8, "popularity": 80},
        {"id": 2, "title": "다른 영화", "genres": ["액션"], "rating": 7, "popularity": 70},
        {"id": 1, "title": "오디세이", "genres": ["액션"], "rating": 8, "popularity": 80},
    ]

    ranked = rank_movies(movies, {"액션": 1.0}, {}, set(), limit=10)

    assert [movie["id"] for movie in ranked] == [1, 2]
