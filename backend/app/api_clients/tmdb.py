"""TMDB에서 시드 데이터와 실시간 개인화 추천 후보를 가져온다.

전역 인기 영화 + 한국 2010년대 영화를 함께 모으는 이유: 제안서 2.2의 NL2SQL
예시("2010년대 한국 영화 중 평점 높은 순")가 시드 데이터만으로 실제 결과를
반환하게 하기 위함.
"""
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

_BASE_URL = "https://api.themoviedb.org/3"

# TMDB 공식 영화 장르표 (움직이지 않는 고정 목록이라 매 요청마다 조회하지 않고 상수로 둔다)
_GENRE_MAP = {
    28: "액션", 12: "모험", 16: "애니메이션", 35: "코미디", 80: "범죄",
    99: "다큐멘터리", 18: "드라마", 10751: "가족", 14: "판타지", 36: "역사",
    27: "공포", 10402: "음악", 9648: "미스터리", 10749: "로맨스",
    878: "SF", 10770: "TV영화", 53: "스릴러", 10752: "전쟁", 37: "서부",
}
_GENRE_ID_BY_NAME = {name: genre_id for genre_id, name in _GENRE_MAP.items()}
_POSTER_BASE_URL = "https://image.tmdb.org/t/p/w500"

_LANGUAGE_COUNTRY_MAP = {
    "ko": "한국", "en": "미국", "ja": "일본", "fr": "프랑스",
    "es": "스페인", "de": "독일", "zh": "중국", "it": "이탈리아",
}


class TMDBClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("TMDB_API_KEY", "")

    def _get(self, path: str, params: dict) -> dict:
        if not self.api_key:
            raise RuntimeError("TMDB_API_KEY가 설정되지 않았습니다.")
        params = {**params, "api_key": self.api_key, "language": "ko-KR"}
        resp = httpx.get(f"{_BASE_URL}{path}", params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def _map_result(self, item: dict) -> dict:
        release_date = item.get("release_date") or ""
        release_year = int(release_date[:4]) if len(release_date) >= 4 else None
        genre_names = [_GENRE_MAP[g] for g in item.get("genre_ids", []) if g in _GENRE_MAP]
        country = _LANGUAGE_COUNTRY_MAP.get(item.get("original_language", ""), item.get("original_language"))
        return {
            "id": item.get("id"),
            "title": item.get("title") or item.get("original_title"),
            "overview": item.get("overview") or "",
            "poster_url": f"{_POSTER_BASE_URL}{item['poster_path']}" if item.get("poster_path") else None,
            "release_year": release_year,
            "genre": ",".join(genre_names),
            "genres": genre_names,
            "rating": item.get("vote_average"),
            "popularity": item.get("popularity", 0),
            "country": country,
        }

    def discover_for_genres(self, genres: list[str], count: int = 30) -> list[dict]:
        """선호 장르를 중심으로 현재 TMDB 후보를 가져온다."""
        genre_ids = [_GENRE_ID_BY_NAME[name] for name in genres if name in _GENRE_ID_BY_NAME]
        params: dict[str, str | int] = {
            "sort_by": "popularity.desc",
            "include_adult": "false",
            "vote_count.gte": 30,
            "page": 1,
        }
        if genre_ids:
            params["with_genres"] = "|".join(str(value) for value in genre_ids)

        first_page = self._get("/discover/movie", params)
        results = list(first_page.get("results", []))
        if count > 20 and first_page.get("total_pages", 1) > 1:
            results.extend(self._get("/discover/movie", {**params, "page": 2}).get("results", []))
        return [self._map_result(item) for item in results[:count]]

    def get_popular_movies(self, count: int = 15) -> list[dict]:
        data = self._get("/discover/movie", {"sort_by": "popularity.desc", "page": 1})
        return [self._map_result(item) for item in data.get("results", [])[:count]]

    def get_korean_movies_2010s(self, count: int = 15) -> list[dict]:
        data = self._get(
            "/discover/movie",
            {
                "with_original_language": "ko",
                "primary_release_date.gte": "2010-01-01",
                "primary_release_date.lte": "2019-12-31",
                "vote_count.gte": 20,
                "sort_by": "vote_average.desc",
                "page": 1,
            },
        )
        return [self._map_result(item) for item in data.get("results", [])[:count]]

    def collect_seed_movies(self) -> list[dict]:
        """중복 제목 제거 후 전역 인기작 + 한국 2010년대작을 합쳐 반환."""
        combined = self.get_popular_movies(15) + self.get_korean_movies_2010s(15)
        seen_titles: set[str] = set()
        unique: list[dict] = []
        for movie in combined:
            if movie["title"] in seen_titles:
                continue
            seen_titles.add(movie["title"])
            unique.append(movie)
        return unique
