from types import SimpleNamespace

from app.routers import chat


def test_explicit_movie_genre_request_is_learned_and_used(monkeypatch):
    captured = {}
    user = SimpleNamespace(id=7)
    profile = SimpleNamespace(confidence_score=0.45)

    monkeypatch.setattr(chat, "get_or_create_user", lambda _session_id: user)
    monkeypatch.setattr(chat, "get_profile_for_user", lambda _user_id: profile)
    monkeypatch.setattr(chat, "profile_preferences", lambda _profile: ({"코미디": 1.0}, {}))
    monkeypatch.setattr(chat, "feedback_movie_ids", lambda _user_id: set())

    def fake_save(user_id, session_id, genre, raw_snippet):
        captured["signal"] = (user_id, session_id, genre, raw_snippet)
        return 0.12

    class FakeTMDBClient:
        def discover_for_genres(self, genres, count, diversity_seed, filters):
            captured["discovery"] = (genres, count, diversity_seed, filters)
            return [{"id": 27, "title": "공포 영화", "release_year": 2026, "rating": 8.1, "genres": ["공포"]}]

    def fake_rank(movies, genres, moods, excluded_ids, limit, confidence, **kwargs):
        captured["ranking"] = {
            "genres": genres,
            "limit": limit,
            "confidence": confidence,
        }
        return movies

    monkeypatch.setattr(chat, "save_conversation_genre_preference", fake_save)
    monkeypatch.setattr(chat, "TMDBClient", FakeTMDBClient)
    monkeypatch.setattr(chat, "rank_movies", fake_rank)

    response = chat._handle_recommend("오늘은 공포영화 추천해줘", "visitor-123")

    assert captured["signal"] == (7, "visitor-123", "공포", "오늘은 공포영화 추천해줘")
    assert captured["discovery"] == (["공포"], 80, "visitor-123", {})
    assert captured["ranking"]["genres"]["공포"] == 0.12
    assert captured["ranking"]["limit"] == 10
    assert response.data["learned_genre"] == "공포"
    assert "가벼운 취향 신호로 기억" in response.reply


def test_rating_and_year_filters_are_applied(monkeypatch):
    captured = {}
    user = SimpleNamespace(id=7)
    profile = SimpleNamespace(confidence_score=0.45)
    monkeypatch.setattr(chat, "get_or_create_user", lambda _session_id: user)
    monkeypatch.setattr(chat, "get_profile_for_user", lambda _user_id: profile)
    monkeypatch.setattr(chat, "profile_preferences", lambda _profile: ({"로맨스": 1.0}, {}))
    monkeypatch.setattr(chat, "feedback_movie_ids", lambda _user_id: set())
    monkeypatch.setattr(chat, "save_conversation_genre_preference", lambda *_args: 1.0)

    class FakeTMDBClient:
        def discover_for_genres(self, genres, count, diversity_seed, filters):
            captured.update(genres=genres, filters=filters)
            return [
                {"id": 1, "title": "통과", "release_year": 2023, "rating": 7.8, "genres": ["로맨스"], "popularity": 10},
                {"id": 4, "title": "새 추천", "release_year": 2022, "rating": 7.6, "genres": ["로맨스"], "popularity": 9},
                {"id": 2, "title": "낮은 평점", "release_year": 2024, "rating": 6.9, "genres": ["로맨스"], "popularity": 100},
                {"id": 3, "title": "오래된 영화", "release_year": 2019, "rating": 8.5, "genres": ["로맨스"], "popularity": 100},
            ]

    monkeypatch.setattr(chat, "TMDBClient", FakeTMDBClient)
    response = chat._handle_recommend(
        "평가 7점 이상인 2020년 이후 로맨스 영화 추천해줘",
        "visitor-123",
        exclude_movie_ids=[1],
    )

    assert captured["genres"] == ["로맨스"]
    assert captured["filters"]["vote_average.gte"] == 7.0
    assert captured["filters"]["primary_release_date.gte"] == "2020-01-01"
    assert [movie["id"] for movie in response.data["movies"]] == [4]
    assert response.data["recommendation_context"]["min_rating"] == 7.0


def test_vague_rating_request_asks_for_threshold():
    response = chat._handle_recommend("평가가 좋은 로맨스 영화 추천해줘", "visitor")

    assert response.data["needs_clarification"] == "min_rating"
    assert "몇 점" in response.reply
