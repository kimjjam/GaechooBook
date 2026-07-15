import pytest

from app.core.scoring.functions import compute_final_score, cosine_similarity


def test_cosine_similarity_identical_vectors_is_one():
    assert cosine_similarity([1, 2, 3], [1, 2, 3]) == 1.0


def test_cosine_similarity_orthogonal_vectors_is_zero():
    assert cosine_similarity([1, 0], [0, 1]) == 0.0


def test_compute_final_score_matches_formula():
    score = compute_final_score(
        confidence=0.8, similarity=0.5, recency_bonus=0.2, popularity_score=0.3, penalty=0.1
    )
    expected = 0.8 * (0.6 * 0.5 + 0.4 * 0.2) + (1 - 0.8) * 0.3 - 0.1
    assert score == pytest.approx(expected)
