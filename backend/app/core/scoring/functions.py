"""제안서 7.1 스코어링 공식의 순수 함수 구현 스텁.

final_score =
    confidence * (0.6 * cosine_sim(user_profile, item_vector) + 0.4 * recency_bonus)
  + (1 - confidence) * popularity_score
  - penalty

실제 벡터화/penalty 규칙은 4단계(개인화 스코어링)에서 구체화한다.
"""
import math


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    if len(vec_a) != len(vec_b):
        raise ValueError("두 벡터의 길이가 같아야 합니다.")
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def compute_final_score(
    confidence: float,
    similarity: float,
    recency_bonus: float,
    popularity_score: float,
    penalty: float = 0.0,
) -> float:
    return (
        confidence * (0.6 * similarity + 0.4 * recency_bonus)
        + (1 - confidence) * popularity_score
        - penalty
    )
