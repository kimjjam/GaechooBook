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
        def discover_for_genres(self, genres, count):
            captured["discovery"] = (genres, count)
            return [{"id": 27, "title": "공포 영화", "release_year": 2026, "rating": 8.1}]

    def fake_rank(movies, genres, moods, excluded_ids, limit, confidence):
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
    assert captured["discovery"] == (["공포"], 40)
    assert captured["ranking"]["genres"]["공포"] == 0.12
    assert captured["ranking"]["limit"] == 10
    assert response.data["learned_genre"] == "공포"
    assert "가벼운 취향 신호로 기억" in response.reply
