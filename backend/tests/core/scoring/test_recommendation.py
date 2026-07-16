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


def test_same_movie_with_different_ids_and_same_poster_is_returned_once():
    movies = [
        {
            "id": 10,
            "title": "벽동",
            "poster_url": "https://image.tmdb.org/t/p/w500/wall.jpg",
            "genres": ["미스터리"],
            "rating": 7,
            "popularity": 80,
        },
        {
            "id": 11,
            "title": "벽동",
            "poster_url": "https://image.tmdb.org/t/p/w500/wall.jpg",
            "genres": ["미스터리"],
            "rating": 7,
            "popularity": 80,
        },
    ]

    ranked = rank_movies(movies, {"미스터리": 1.0}, {}, set(), limit=10)

    assert [movie["id"] for movie in ranked] == [10]


def test_disliked_genre_is_penalized():
    movies = [
        {"id": 1, "title": "선호 영화", "genres": ["코미디"], "rating": 8, "popularity": 80},
        {"id": 2, "title": "비선호 영화", "genres": ["공포"], "rating": 8, "popularity": 80},
    ]

    ranked = rank_movies(
        movies,
        {"코미디": 1.0, "공포": -0.15},
        {},
        set(),
        limit=2,
    )

    assert [movie["id"] for movie in ranked] == [1, 2]
    assert ranked[0]["score"] > ranked[1]["score"]
