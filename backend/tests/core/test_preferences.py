from app.core.preferences import preferred_genres, updated_genre_weight


def test_only_meaningful_positive_genres_are_preferred():
    weights = {
        "코미디": 1.0,
        "드라마": 0.5,
        "공포": 0.35,
        "스릴러": -0.15,
    }

    assert preferred_genres(weights) == ["코미디", "드라마"]


def test_feedback_for_unseen_genre_starts_from_neutral():
    assert updated_genre_weight(None, "liked") == 0.2
    assert updated_genre_weight(None, "disliked") == -0.15


def test_repeated_feedback_is_clamped_in_both_directions():
    assert updated_genre_weight(1.95, "liked") == 2.0
    assert updated_genre_weight(-1.95, "disliked") == -2.0
