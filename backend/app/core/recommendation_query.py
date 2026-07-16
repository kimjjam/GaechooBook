"""영화 추천 발화에서 확정적인 검색 조건을 추출하고 누적한다.

LLM 응답에만 의존하지 않아 숫자 조건을 놓치지 않으며, 직렬화 가능한 모델이라
서버리스 환경에서도 클라이언트가 이전 조건을 다음 요청에 전달할 수 있다.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any


MOVIE_GENRES = (
    "액션", "모험", "애니메이션", "코미디", "범죄", "다큐멘터리", "드라마", "가족",
    "판타지", "역사", "공포", "음악", "미스터리", "로맨스", "SF", "스릴러", "전쟁", "서부",
)

_COUNTRIES = {
    "한국": "KR", "국내": "KR", "미국": "US", "일본": "JP", "프랑스": "FR",
    "영국": "GB", "중국": "CN", "독일": "DE", "이탈리아": "IT", "스페인": "ES",
}

_MOODS = {
    "가볍고 유쾌한": ("가볍", "유쾌", "웃", "편하게"),
    "따뜻하고 편안한": ("따뜻", "편안", "힐링"),
    "긴장감 있는": ("긴장", "쫄깃", "무서", "오싹"),
    "상상력을 자극하는": ("상상력", "신비", "환상적"),
    "감동적인": ("감동", "눈물", "뭉클"),
}


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


@dataclass
class RecommendationQuery:
    genres: list[str] = field(default_factory=list)
    excluded_genres: list[str] = field(default_factory=list)
    moods: list[str] = field(default_factory=list)
    min_rating: float | None = None
    max_rating: float | None = None
    year_from: int | None = None
    year_to: int | None = None
    max_runtime: int | None = None
    country: str | None = None
    country_name: str | None = None
    similar_to: str | None = None
    limit: int = 10
    sort_by: str = "personalized"

    @classmethod
    def from_dict(cls, value: dict[str, Any] | None) -> "RecommendationQuery":
        if not value:
            return cls()
        allowed = cls.__dataclass_fields__.keys()
        clean = {key: value[key] for key in allowed if key in value}
        try:
            query = cls(**clean)
        except (TypeError, ValueError):
            return cls()
        raw_genres = query.genres if isinstance(query.genres, list) else []
        raw_excluded = query.excluded_genres if isinstance(query.excluded_genres, list) else []
        raw_moods = query.moods if isinstance(query.moods, list) else []
        query.genres = [genre for genre in raw_genres if genre in MOVIE_GENRES]
        query.excluded_genres = [genre for genre in raw_excluded if genre in MOVIE_GENRES]
        query.moods = [mood for mood in raw_moods if mood in _MOODS]

        def optional_float(raw: Any, minimum: float, maximum: float) -> float | None:
            if raw is None:
                return None
            try:
                number = float(raw)
            except (TypeError, ValueError):
                return None
            return number if minimum <= number <= maximum else None

        def optional_int(raw: Any, minimum: int, maximum: int) -> int | None:
            number = optional_float(raw, minimum, maximum)
            return int(number) if number is not None else None

        query.min_rating = optional_float(query.min_rating, 0, 10)
        query.max_rating = optional_float(query.max_rating, 0, 10)
        query.year_from = optional_int(query.year_from, 1888, date.today().year + 5)
        query.year_to = optional_int(query.year_to, 1888, date.today().year + 5)
        query.max_runtime = optional_int(query.max_runtime, 1, 600)
        query.country = query.country if query.country in _COUNTRIES.values() else None
        query.country_name = (
            query.country_name if query.country_name in {"한국", *_COUNTRIES.keys()} else None
        )
        query.similar_to = (
            str(query.similar_to).strip()[:100] if query.similar_to else None
        )
        query.sort_by = query.sort_by if query.sort_by in {"personalized", "rating", "recent"} else "personalized"
        try:
            query.limit = max(1, min(20, int(query.limit or 10)))
        except (TypeError, ValueError):
            query.limit = 10
        return query

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def tmdb_filters(self) -> dict[str, str | int | float]:
        filters: dict[str, str | int | float] = {}
        if self.min_rating is not None:
            filters["vote_average.gte"] = self.min_rating
        if self.max_rating is not None:
            filters["vote_average.lte"] = self.max_rating
        if self.year_from is not None:
            filters["primary_release_date.gte"] = f"{self.year_from}-01-01"
        if self.year_to is not None:
            filters["primary_release_date.lte"] = f"{self.year_to}-12-31"
        if self.max_runtime is not None:
            filters["with_runtime.lte"] = self.max_runtime
        if self.country:
            filters["with_origin_country"] = self.country
        return filters

    def apply(self, movies: list[dict]) -> list[dict]:
        """TMDB 조건을 최종 결과에서도 검증한다(런타임은 목록 응답에 없어 API에 위임)."""
        result = []
        for movie in movies:
            rating = float(movie.get("rating") or 0)
            year = movie.get("release_year")
            genres = set(movie.get("genres") or [])
            if self.genres and not genres.intersection(self.genres):
                continue
            if self.min_rating is not None and rating < self.min_rating:
                continue
            if self.max_rating is not None and rating > self.max_rating:
                continue
            if self.year_from is not None and (year is None or int(year) < self.year_from):
                continue
            if self.year_to is not None and (year is None or int(year) > self.year_to):
                continue
            if genres & set(self.excluded_genres):
                continue
            movie_country = str(movie.get("country") or "")
            if self.country_name and movie_country and movie_country != self.country_name:
                continue
            result.append(movie)
        return result

    def describe(self) -> str:
        parts: list[str] = []
        if self.genres:
            parts.append("·".join(self.genres))
        if self.min_rating is not None:
            parts.append(f"평점 {self.min_rating:g} 이상")
        if self.max_rating is not None:
            parts.append(f"평점 {self.max_rating:g} 이하")
        if self.year_from is not None:
            parts.append(f"{self.year_from}년 이후")
        if self.year_to is not None:
            parts.append(f"{self.year_to}년 이전")
        if self.max_runtime is not None:
            parts.append(f"{self.max_runtime}분 이내")
        if self.country_name:
            parts.append(f"{self.country_name} 영화")
        if self.excluded_genres:
            parts.append(f"{'·'.join(self.excluded_genres)} 제외")
        if self.similar_to:
            parts.append(f"‘{self.similar_to}’ 유사작")
        return ", ".join(parts) or "저장된 취향"


@dataclass
class ParsedRecommendation:
    query: RecommendationQuery
    changed: bool
    needs_rating_clarification: bool = False
    durable_dislikes: list[str] = field(default_factory=list)


def _number_match(text: str, direction: str) -> float | None:
    if direction == "min":
        suffix = r"(?:이상|넘(?:는|게|는\s*것)?|초과)"
    else:
        suffix = r"(?:이하|안(?:\s*)넘(?:는|게)?|미만)"
    match = re.search(rf"(?:평점|평가)?\s*(\d+(?:\.\d+)?)\s*점?\s*{suffix}", text)
    return float(match.group(1)) if match else None


def parse_recommendation_query(
    message: str,
    previous: dict[str, Any] | None = None,
) -> ParsedRecommendation:
    text = " ".join(message.strip().split())
    query = RecommendationQuery.from_dict(previous)
    before = query.to_dict()

    reset = any(phrase in text for phrase in ("조건 초기화", "조건 지워", "처음부터", "새로 찾아"))
    if reset:
        query = RecommendationQuery()

    found_genres: list[str] = []
    excluded: list[str] = []
    durable_dislikes: list[str] = []
    for genre in MOVIE_GENRES:
        if genre.casefold() not in text.casefold():
            continue
        window = re.search(rf"{re.escape(genre)}.{{0,12}}", text, re.IGNORECASE)
        tail = window.group(0) if window else genre
        if re.search(r"(빼|제외|말고|싫|별로|안\s*좋)", tail):
            excluded.append(genre)
            if re.search(r"(싫|별로|안\s*좋)", tail):
                durable_dislikes.append(genre)
        else:
            found_genres.append(genre)

    if found_genres:
        query.genres = _unique(found_genres)
        query.excluded_genres = [g for g in query.excluded_genres if g not in found_genres]
    if excluded:
        query.excluded_genres = _unique(query.excluded_genres + excluded)
        query.genres = [g for g in query.genres if g not in excluded]

    min_rating = _number_match(text, "min")
    max_rating = _number_match(text, "max")
    if min_rating is not None and 0 <= min_rating <= 10:
        query.min_rating = min_rating
    if max_rating is not None and 0 <= max_rating <= 10:
        query.max_rating = max_rating

    year_from = re.search(r"((?:19|20)\d{2})\s*년?\s*(?:이후|부터|이상)", text)
    year_to = re.search(r"((?:19|20)\d{2})\s*년?\s*(?:이전|까지|이하)", text)
    if year_from:
        query.year_from = min(date.today().year + 5, int(year_from.group(1)))
    if year_to:
        query.year_to = int(year_to.group(1))

    runtime = re.search(r"(\d+(?:\.\d+)?)\s*(시간|분)\s*(?:이내|이하|안(?:에)?|미만)", text)
    if runtime:
        value = float(runtime.group(1))
        query.max_runtime = round(value * 60) if runtime.group(2) == "시간" else round(value)

    for name, code in _COUNTRIES.items():
        if name in text:
            query.country = code
            query.country_name = "한국" if name == "국내" else name
            break

    found_moods = [mood for mood, words in _MOODS.items() if any(word in text for word in words)]
    if found_moods:
        query.moods = _unique(found_moods)

    similar = re.search(
        r"([^,.?!]{1,40}?)(?:(?:와|과)\s*비슷한|처럼|같은|비슷한)\s*"
        r"(?:느낌|분위기|영화|작품)?(?:의)?\s*(?:영화|작품|거)?(?:를|을)?\s*(?:추천|찾|보여)",
        text,
    )
    if similar:
        title = re.sub(r"^(?:영화\s*)?", "", similar.group(1)).strip(" ‘’\"'")
        title = re.sub(r"^(?:이|그|저)\s*", "", title)
        if 1 < len(title) <= 40:
            query.similar_to = title

    count = re.search(r"(\d+)\s*(?:개|편)\b", text)
    if count:
        query.limit = max(1, min(20, int(count.group(1))))
    if "평점순" in text or "평점 높은 순" in text:
        query.sort_by = "rating"
    elif "최신" in text:
        query.sort_by = "recent"
    if re.search(r"슬프.{0,6}(?:빼|제외|말고|싫)", text):
        query.moods = _unique(query.moods + ["가볍고 유쾌한"])

    vague_rating = bool(re.search(r"(?:평점|평가)(?:이|가)?\s*(?:좋|높)", text))
    needs_clarification = vague_rating and min_rating is None and query.min_rating is None
    return ParsedRecommendation(
        query=query,
        changed=query.to_dict() != before,
        needs_rating_clarification=needs_clarification,
        durable_dislikes=durable_dislikes,
    )


def looks_like_recommendation_followup(message: str) -> bool:
    if any(genre.casefold() in message.casefold() for genre in MOVIE_GENRES):
        return True
    if any(country in message for country in _COUNTRIES):
        return True
    return bool(re.search(
        r"(이상|이하|이내|이후|이전|부터|까지|빼고|제외|말고|싫어|별로|"
        r"최신|초기화|처음부터|새로\s*찾|더\s*(?:높|낮|짧|길|최신)|"
        r"가볍|따뜻|긴장|감동|분|시간|점)",
        message,
    ))
