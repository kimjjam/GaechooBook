import math

from app.core.preferences import preferred_genres
from app.core.scoring.functions import compute_final_score


_MOOD_GENRES = {
    "가볍고 유쾌한": {"코미디", "가족", "애니메이션"},
    "따뜻하고 편안한": {"드라마", "가족", "로맨스"},
    "긴장감 있는": {"스릴러", "범죄", "미스터리", "공포"},
    "상상력을 자극하는": {"SF", "판타지", "모험"},
    "감동적인": {"드라마", "로맨스", "음악"},
}


def _movie_identity(movie: dict) -> tuple[str, ...]:
    poster_url = str(movie.get("poster_url") or "").strip()
    if poster_url:
        return ("poster", poster_url)
    normalized_title = " ".join(str(movie.get("title") or "").casefold().split())
    return ("title_year", normalized_title, str(movie.get("release_year") or ""))


def rank_movies(
    movies: list[dict],
    genre_weights: dict[str, float],
    mood_weights: dict[str, float],
    excluded_ids: set[int],
    limit: int = 8,
    confidence: float = 0.72,
    requested_genres: list[str] | None = None,
    requested_moods: list[str] | None = None,
    query_description: str | None = None,
) -> list[dict]:
    preferred = set(preferred_genres(genre_weights))
    disliked = {genre for genre, weight in genre_weights.items() if float(weight) < 0}
    mood_genres: set[str] = set()
    for mood, weight in mood_weights.items():
        if float(weight) > 0:
            mood_genres.update(_MOOD_GENRES.get(mood, set()))
    for mood in requested_moods or []:
        mood_genres.update(_MOOD_GENRES.get(mood, set()))
    explicit_genres = set(requested_genres or [])

    ranked: list[dict] = []
    seen_ids = set(excluded_ids)
    seen_movie_identities: set[tuple[str, ...]] = set()
    for movie in movies:
        movie_id = movie.get("id")
        if movie_id is None:
            continue
        normalized_id = int(movie_id)
        if normalized_id in seen_ids:
            continue
        movie_identity = _movie_identity(movie)
        if movie_identity in seen_movie_identities:
            continue
        seen_ids.add(normalized_id)
        seen_movie_identities.add(movie_identity)

        genres = set(movie.get("genres", []))
        matched = genres & preferred
        max_weight = max((float(genre_weights.get(genre, 0)) for genre in matched), default=0)
        genre_fit = min(1.0, max_weight / 1.5)
        mood_fit = min(1.0, len(genres & mood_genres) / 2) if mood_genres else 0.5
        similarity = 0.75 * genre_fit + 0.25 * mood_fit
        rating = float(movie.get("rating") or 0) / 10
        # 인기도 차이를 완만하게 만들어 취향과 평점이 최종 순위에 더 잘 반영되게 한다.
        popularity = min(
            1.0,
            math.log1p(float(movie.get("popularity") or 0)) / math.log1p(1000),
        )
        disliked_strength = max(
            (abs(float(genre_weights.get(genre, 0))) for genre in genres & disliked),
            default=0.0,
        )
        score = compute_final_score(
            confidence=max(0.0, min(1.0, confidence)),
            similarity=similarity,
            recency_bonus=rating,
            popularity_score=popularity,
            penalty=min(0.35, disliked_strength),
        )

        explicit_match = genres & explicit_genres
        reasons: list[str] = []
        if explicit_match:
            reasons.append(f"요청한 {', '.join(sorted(explicit_match))} 장르")
        elif matched:
            reasons.append(f"좋아하는 {', '.join(sorted(matched))} 장르")
        elif genres & mood_genres:
            reasons.append("선택한 감상 분위기")
        else:
            reasons.append("취향을 넓혀볼 만한 인기 작품")
        reasons.append(f"평점 {float(movie.get('rating') or 0):.1f}")
        if query_description:
            reasons.append(f"{query_description} 조건 충족")
        reason = " · ".join(reasons)

        ranked.append({**movie, "score": round(score, 3), "reason": reason})

    return sorted(ranked, key=lambda item: (item["score"], item.get("rating") or 0), reverse=True)[:limit]
