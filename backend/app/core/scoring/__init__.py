"""추천 스코어링 순수 함수 모음.

DB 접근, API 호출 등 부수효과를 절대 추가하지 않는다. 입력(벡터/프로필) →
출력(점수)만 다루며, pytest로 항상 테스트 가능한 상태를 유지한다.
"""
from app.core.scoring.functions import compute_final_score, cosine_similarity

__all__ = ["cosine_similarity", "compute_final_score"]
