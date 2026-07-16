from types import SimpleNamespace

from app.routers import personalization
from app.schemas.personalization import FeedbackBatchRequest


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


def test_resolve_user_keeps_authenticated_user_separate_from_visitor_token(monkeypatch):
    account_user = SimpleNamespace(id=42)
    monkeypatch.setattr(personalization, "session_cookie", lambda _request: "session-token")
    monkeypatch.setattr(
        personalization,
        "get_auth_context",
        lambda _token: SimpleNamespace(user=account_user, csrf_hash="csrf-hash"),
    )
    monkeypatch.setattr(
        personalization,
        "get_or_create_user",
        lambda _token: (_ for _ in ()).throw(AssertionError("visitor user must not be used")),
    )

    resolved = personalization._resolve_user(object(), "another-visitor-token")

    assert resolved.id == 42


def test_resolve_user_uses_exact_anonymous_visitor_token(monkeypatch):
    captured = {}
    visitor_user = SimpleNamespace(id=7)
    monkeypatch.setattr(personalization, "session_cookie", lambda _request: None)
    monkeypatch.setattr(
        personalization,
        "get_or_create_user",
        lambda token: captured.update(token=token) or visitor_user,
    )

    resolved = personalization._resolve_user(object(), "visitor-user-a")

    assert resolved.id == 7
    assert captured["token"] == "visitor-user-a"


def test_recommendations_exclude_ids_requested_by_client(monkeypatch):
    user = SimpleNamespace(id=7)
    profile = SimpleNamespace(confidence_score=0.45)

    monkeypatch.setattr(personalization, "_resolve_user", lambda *_args, **_kwargs: user)
    monkeypatch.setattr(personalization, "get_profile_for_user", lambda _user_id: profile)
    monkeypatch.setattr(personalization, "profile_preferences", lambda _profile: ({"액션": 1.0}, {}))
    monkeypatch.setattr(personalization, "feedback_movie_ids", lambda _user_id: {1})

    class FakeTMDBClient:
        def discover_for_genres(
            self, genres, count, diversity_seed, excluded_ids=None, require_all_genres=False,
        ):
            assert count == 80
            if genres:
                assert diversity_seed == "7:1,2"
            else:
                assert diversity_seed == "7:1,2:all-catalog"
            return [_movie(1), _movie(2), _movie(3)]

    monkeypatch.setattr(personalization, "TMDBClient", FakeTMDBClient)

    response = personalization.get_recommendations(
        http_request=object(),
        visitor_token="visitor-123",
        limit=10,
        exclude_movie_ids="2,not-a-number",
    )

    assert [movie.id for movie in response.recommendations] == [3]


def test_feedback_batch_is_saved_in_one_repository_call(monkeypatch):
    user = SimpleNamespace(id=7)
    captured = {}
    monkeypatch.setattr(personalization, "_resolve_user", lambda *_args, **_kwargs: user)
    monkeypatch.setattr(
        personalization,
        "get_profile_for_user",
        lambda _user_id: SimpleNamespace(id=1),
    )
    monkeypatch.setattr(
        personalization,
        "save_feedback_batch",
        lambda user_id, feedback: captured.update(user_id=user_id, feedback=feedback),
    )

    response = personalization.record_feedback_batch(
        request=FeedbackBatchRequest(
            visitor_token="visitor-123",
            feedback=[
                {
                    "movie_id": movie_id,
                    "movie_title": f"영화 {movie_id}",
                    "genres": ["액션"],
                    "action": "liked" if movie_id % 2 else "disliked",
                }
                for movie_id in range(1, 6)
            ],
        ),
        http_request=object(),
        x_csrf_token=None,
    )

    assert response.saved_count == 5
    assert captured["user_id"] == 7
    assert [item["movie_id"] for item in captured["feedback"]] == [1, 2, 3, 4, 5]


def test_recommendations_do_not_send_weak_or_disliked_genres_to_tmdb(monkeypatch):
    user = SimpleNamespace(id=11)
    profile = SimpleNamespace(confidence_score=0.45)
    captured = {"genre_calls": []}

    monkeypatch.setattr(personalization, "_resolve_user", lambda *_args, **_kwargs: user)
    monkeypatch.setattr(personalization, "get_profile_for_user", lambda _user_id: profile)
    monkeypatch.setattr(
        personalization,
        "profile_preferences",
        lambda _profile: (
            {"코미디": 1.0, "공포": 0.35, "스릴러": -0.15},
            {},
        ),
    )
    monkeypatch.setattr(personalization, "feedback_movie_ids", lambda _user_id: set())

    class FakeTMDBClient:
        def discover_for_genres(
            self, genres, count, diversity_seed, excluded_ids=None, require_all_genres=False,
        ):
            captured["genre_calls"].append((genres, require_all_genres))
            return []

    monkeypatch.setattr(personalization, "TMDBClient", FakeTMDBClient)

    personalization.get_recommendations(
        http_request=object(),
        visitor_token="visitor-123",
        limit=10,
        exclude_movie_ids="",
    )

    assert captured["genre_calls"] == [(["코미디"], False), ([], False)]


def test_recommendations_expand_to_all_catalog_when_preferred_genre_is_exhausted(monkeypatch):
    user = SimpleNamespace(id=12)
    profile = SimpleNamespace(confidence_score=0.7)
    calls = []
    monkeypatch.setattr(personalization, "_resolve_user", lambda *_args, **_kwargs: user)
    monkeypatch.setattr(personalization, "get_profile_for_user", lambda _user_id: profile)
    monkeypatch.setattr(personalization, "profile_preferences", lambda _profile: ({"로맨스": 1.0}, {}))
    monkeypatch.setattr(personalization, "feedback_movie_ids", lambda _user_id: {1})

    class FakeTMDBClient:
        def discover_for_genres(
            self, genres, count, diversity_seed, excluded_ids=None, require_all_genres=False,
        ):
            calls.append((genres, excluded_ids, require_all_genres))
            return [] if genres else [_movie(9), _movie(10)]

    monkeypatch.setattr(personalization, "TMDBClient", FakeTMDBClient)

    response = personalization.get_recommendations(
        http_request=object(),
        visitor_token="visitor-123",
        limit=2,
        exclude_movie_ids="",
    )

    assert [movie.id for movie in response.recommendations] == [9, 10]
    assert calls[0][0] == ["로맨스"]
    assert calls[1][0] == []


def test_recommendations_relax_from_all_to_any_preferred_genre(monkeypatch):
    user = SimpleNamespace(id=13)
    profile = SimpleNamespace(confidence_score=0.7)
    calls = []
    monkeypatch.setattr(personalization, "_resolve_user", lambda *_args, **_kwargs: user)
    monkeypatch.setattr(personalization, "get_profile_for_user", lambda _user_id: profile)
    monkeypatch.setattr(
        personalization,
        "profile_preferences",
        lambda _profile: ({"로맨스": 1.0, "코미디": 0.9}, {}),
    )
    monkeypatch.setattr(personalization, "feedback_movie_ids", lambda _user_id: set())

    class FakeTMDBClient:
        def discover_for_genres(
            self, genres, count, diversity_seed, excluded_ids=None, require_all_genres=False,
        ):
            calls.append((genres, require_all_genres))
            if require_all_genres:
                return [_movie(20)]
            if genres:
                return [_movie(21), _movie(22)]
            return []

    monkeypatch.setattr(personalization, "TMDBClient", FakeTMDBClient)

    response = personalization.get_recommendations(
        http_request=object(),
        visitor_token="visitor-123",
        limit=3,
        exclude_movie_ids="",
    )

    assert [movie.id for movie in response.recommendations] == [20, 21, 22]
    assert calls[:2] == [(["로맨스", "코미디"], True), (["로맨스", "코미디"], False)]


def test_recommendations_require_only_two_strongest_genres_first(monkeypatch):
    user = SimpleNamespace(id=14)
    profile = SimpleNamespace(confidence_score=0.7)
    calls = []
    monkeypatch.setattr(personalization, "_resolve_user", lambda *_args, **_kwargs: user)
    monkeypatch.setattr(personalization, "get_profile_for_user", lambda _user_id: profile)
    monkeypatch.setattr(
        personalization,
        "profile_preferences",
        lambda _profile: ({"가족": 0.6, "로맨스": 1.4, "코미디": 1.1}, {}),
    )
    monkeypatch.setattr(personalization, "feedback_movie_ids", lambda _user_id: set())

    class FakeTMDBClient:
        def discover_for_genres(
            self, genres, count, diversity_seed, excluded_ids=None, require_all_genres=False,
        ):
            calls.append((genres, require_all_genres))
            return [_movie(30), _movie(31)]

    monkeypatch.setattr(personalization, "TMDBClient", FakeTMDBClient)

    personalization.get_recommendations(
        http_request=object(),
        visitor_token="visitor-123",
        limit=2,
        exclude_movie_ids="",
    )

    assert calls[0] == (["로맨스", "코미디"], True)


def test_recommendations_try_either_primary_genre_before_other_preferences(monkeypatch):
    user = SimpleNamespace(id=16)
    profile = SimpleNamespace(confidence_score=0.7)
    calls = []
    monkeypatch.setattr(personalization, "_resolve_user", lambda *_args, **_kwargs: user)
    monkeypatch.setattr(personalization, "get_profile_for_user", lambda _user_id: profile)
    monkeypatch.setattr(
        personalization,
        "profile_preferences",
        lambda _profile: ({"가족": 0.7, "로맨스": 1.4, "코미디": 1.1}, {}),
    )
    monkeypatch.setattr(personalization, "feedback_movie_ids", lambda _user_id: set())

    class FakeTMDBClient:
        def discover_for_genres(
            self, genres, count, diversity_seed, excluded_ids=None, require_all_genres=False,
        ):
            calls.append((genres, require_all_genres))
            if require_all_genres:
                return []
            if genres == ["로맨스", "코미디"]:
                return [_movie(40)]
            if genres:
                return [_movie(41)]
            return []

    monkeypatch.setattr(personalization, "TMDBClient", FakeTMDBClient)

    response = personalization.get_recommendations(
        http_request=object(),
        visitor_token="visitor-123",
        limit=2,
        exclude_movie_ids="",
    )

    assert [movie.id for movie in response.recommendations] == [40, 41]
    assert calls[:3] == [
        (["로맨스", "코미디"], True),
        (["로맨스", "코미디"], False),
        (["가족", "로맨스", "코미디"], False),
    ]


def test_liked_movies_returns_latest_saved_likes_with_tmdb_details(monkeypatch):
    user = SimpleNamespace(id=15)
    monkeypatch.setattr(personalization, "_resolve_user", lambda *_args, **_kwargs: user)
    monkeypatch.setattr(
        personalization,
        "liked_movies_for_user",
        lambda user_id, limit: [{"id": 44, "title": "저장 제목", "genres": ["드라마"]}],
    )

    class FakeTMDBClient:
        def get_movie_details(self, movie_id):
            return {
                **_movie(movie_id),
                "backdrop_url": None,
                "release_date": "2026-01-01",
                "runtime": 110,
                "tagline": None,
                "trailer_url": None,
            }

    monkeypatch.setattr(personalization, "TMDBClient", FakeTMDBClient)

    response = personalization.get_liked_movies(
        http_request=object(),
        visitor_token="visitor-123",
        limit=30,
    )

    assert [movie.id for movie in response.recommendations] == [44]
    assert response.recommendations[0].reason == "좋아요한 영화"
