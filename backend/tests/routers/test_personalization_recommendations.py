from types import SimpleNamespace

from app.routers import personalization


def _movie(movie_id: int) -> dict:
    return {
        "id": movie_id,
        "title": f"영화 {movie_id}",
        "overview": "줄거리",
        "poster_url": None,
        "release_year": 2026,
        "rating": 8.0,
        "genres": ["액션"],
        "popularity": 100,
    }


def test_recommendations_exclude_ids_requested_by_client(monkeypatch):
    user = SimpleNamespace(id=7)
    profile = SimpleNamespace(confidence_score=0.45)

    monkeypatch.setattr(personalization, "_resolve_user", lambda *_args, **_kwargs: user)
    monkeypatch.setattr(personalization, "get_profile_for_user", lambda _user_id: profile)
    monkeypatch.setattr(personalization, "profile_preferences", lambda _profile: ({"액션": 1.0}, {}))
    monkeypatch.setattr(personalization, "feedback_movie_ids", lambda _user_id: {1})

    class FakeTMDBClient:
        def discover_for_genres(self, _genres, count):
            assert count == 40
            return [_movie(1), _movie(2), _movie(3)]

    monkeypatch.setattr(personalization, "TMDBClient", FakeTMDBClient)

    response = personalization.get_recommendations(
        http_request=object(),
        visitor_token="visitor-123",
        limit=10,
        exclude_movie_ids="2,not-a-number",
    )

    assert [movie.id for movie in response.recommendations] == [3]
