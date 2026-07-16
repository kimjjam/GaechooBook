"""TMDB에서 시드 데이터와 실시간 개인화 추천 후보를 가져온다.

전역 인기 영화 + 한국 2010년대 영화를 함께 모으는 이유: 제안서 2.2의 NL2SQL
예시("2010년대 한국 영화 중 평점 높은 순")가 시드 데이터만으로 실제 결과를
반환하게 하기 위함.
"""
import hashlib
import logging
import os
import random
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Lock

import httpx
from dotenv import load_dotenv

load_dotenv()

_BASE_URL = "https://api.themoviedb.org/3"
_MAX_REQUEST_ATTEMPTS = 2
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
logger = logging.getLogger(__name__)
_http_client: httpx.Client | None = None
_http_client_lock = Lock()


def _get_http_client() -> httpx.Client:
    global _http_client
    if _http_client is None:
        with _http_client_lock:
            if _http_client is None:
                _http_client = httpx.Client(
                    timeout=httpx.Timeout(8, connect=5),
                    limits=httpx.Limits(
                        max_connections=2,
                        max_keepalive_connections=2,
                        keepalive_expiry=30,
                    ),
                )
    return _http_client

# TMDB 공식 영화 장르표 (움직이지 않는 고정 목록이라 매 요청마다 조회하지 않고 상수로 둔다)
_GENRE_MAP = {
    28: "액션", 12: "모험", 16: "애니메이션", 35: "코미디", 80: "범죄",
    99: "다큐멘터리", 18: "드라마", 10751: "가족", 14: "판타지", 36: "역사",
    27: "공포", 10402: "음악", 9648: "미스터리", 10749: "로맨스",
    878: "SF", 10770: "TV영화", 53: "스릴러", 10752: "전쟁", 37: "서부",
}
_GENRE_ID_BY_NAME = {name: genre_id for genre_id, name in _GENRE_MAP.items()}
_POSTER_BASE_URL = "https://image.tmdb.org/t/p/w500"
_BACKDROP_BASE_URL = "https://image.tmdb.org/t/p/w1280"

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
        for attempt in range(_MAX_REQUEST_ATTEMPTS):
            try:
                response = _get_http_client().get(
                    f"{_BASE_URL}{path}",
                    params=params,
                )
                if (
                    response.status_code not in _RETRYABLE_STATUS_CODES
                    or attempt == _MAX_REQUEST_ATTEMPTS - 1
                ):
                    response.raise_for_status()
                    return response.json()
            except httpx.TransportError:
                if attempt == _MAX_REQUEST_ATTEMPTS - 1:
                    raise
            time.sleep(0.2 * (attempt + 1))
        raise RuntimeError("TMDB 요청 재시도 상태가 올바르지 않습니다.")

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

    def discover_for_genres(
        self,
        genres: list[str],
        count: int = 30,
        diversity_seed: str | int | None = None,
        filters: dict[str, str | int | float] | None = None,
        excluded_ids: set[int] | None = None,
        require_all_genres: bool = False,
    ) -> list[dict]:
        """선호 장르 안에서 인기작, 평점작, 최신작을 다양하게 가져온다."""
        genre_ids = [_GENRE_ID_BY_NAME[name] for name in genres if name in _GENRE_ID_BY_NAME]
        base_params: dict[str, str | int] = {
            "include_adult": "false",
            "include_video": "false",
            "primary_release_date.lte": date.today().isoformat(),
        }
        if genre_ids:
            delimiter = "," if require_all_genres else "|"
            base_params["with_genres"] = delimiter.join(str(value) for value in genre_ids)
        if filters:
            base_params.update(filters)

        seed_value = str(diversity_seed) if diversity_seed is not None else "|".join(sorted(genres))
        digest = hashlib.sha256(seed_value.encode("utf-8")).digest()
        initial_request_params = [
            {"sort_by": "popularity.desc", "vote_count.gte": 50, "page": 1},
            {"sort_by": "popularity.desc", "vote_count.gte": 30, "page": 2 + digest[0] % 7},
            {"sort_by": "vote_average.desc", "vote_count.gte": 200, "page": 1 + digest[1] % 5},
            {
                "sort_by": "primary_release_date.desc",
                "primary_release_date.lte": date.today().isoformat(),
                "vote_count.gte": 20,
                "page": 1 + digest[2] % 5,
            },
        ]
        unique_results: list[dict] = []
        seen_ids: set[int] = set()
        blocked_ids = {int(movie_id) for movie_id in (excluded_ids or set())}

        def collect(request_params: list[dict[str, str | int]]) -> bool:
            queries = [{**base_params, **query_params} for query_params in request_params]
            responses: list[dict] = []
            request_errors: list[httpx.HTTPError] = []
            with ThreadPoolExecutor(max_workers=min(8, len(queries))) as executor:
                futures = [
                    executor.submit(self._get, "/discover/movie", params)
                    for params in queries
                ]
                for params, future in zip(queries, futures):
                    try:
                        responses.append(future.result())
                    except httpx.HTTPError as exc:
                        request_errors.append(exc)
                        logger.warning(
                            "TMDB discovery request failed; continuing with remaining pages",
                            extra={
                                "sort_by": params.get("sort_by"),
                                "page": params.get("page"),
                                "error_type": type(exc).__name__,
                            },
                        )
            if not responses and request_errors:
                raise request_errors[0]
            for data in responses:
                for item in data.get("results", []):
                    movie_id = item.get("id")
                    if movie_id is None or movie_id in blocked_ids or movie_id in seen_ids:
                        continue
                    seen_ids.add(movie_id)
                    unique_results.append(item)
                    if len(unique_results) >= count:
                        return True
            return False

        if collect(initial_request_params):
            return [self._map_result(result) for result in unique_results]

        # 최근 노출작이 많으면 기본 4페이지만으로 후보가 고갈될 수 있다. 이때만
        # 더 넓은 페이지를 조회해 실제로 새로운 후보를 채운다.
        if blocked_ids:
            page_rng = random.Random(int.from_bytes(digest[:8], "big"))
            # TMDB discover는 최대 500페이지까지 탐색할 수 있다. 이미 본 영화가
            # 많을수록 앞쪽 인기 페이지에만 머물지 않고 전체 카탈로그에서 고르게
            # 페이지를 뽑아, 오래된 작품과 덜 알려진 작품도 후보에 들어오게 한다.
            popularity_pages = page_rng.sample(range(2, 501), 8)
            rating_pages = page_rng.sample(range(2, 501), 4)
            recent_pages = page_rng.sample(range(2, 501), 4)
            expanded_request_params = [
                *(
                    {"sort_by": "popularity.desc", "vote_count.gte": 20, "page": page}
                    for page in popularity_pages
                ),
                *(
                    {"sort_by": "vote_average.desc", "vote_count.gte": 100, "page": page}
                    for page in rating_pages
                ),
                *(
                    {
                        "sort_by": "primary_release_date.desc",
                        "primary_release_date.lte": date.today().isoformat(),
                        "vote_count.gte": 10,
                        "page": page,
                    }
                    for page in recent_pages
                ),
            ]
            for offset in range(0, len(expanded_request_params), 4):
                if collect(expanded_request_params[offset : offset + 4]):
                    break
        return [self._map_result(result) for result in unique_results]

    def recommend_similar(
        self,
        title: str,
        count: int = 40,
        filters: dict[str, str | int | float] | None = None,
    ) -> list[dict]:
        """제목으로 기준 영화를 찾고 TMDB 유사 추천 결과를 반환한다."""
        search = self._get("/search/movie", {"query": title, "include_adult": "false"})
        matches = search.get("results", [])
        if not matches:
            return []
        movie_id = matches[0].get("id")
        if movie_id is None:
            return []

        candidates: list[dict] = []
        seen_ids: set[int] = set()
        for page in (1, 2):
            data = self._get(f"/movie/{movie_id}/recommendations", {"page": page})
            for item in data.get("results", []):
                mapped = self._map_result(item)
                mapped_id = mapped.get("id")
                if mapped_id is None or mapped_id in seen_ids:
                    continue
                seen_ids.add(mapped_id)
                candidates.append(mapped)

        active_filters = filters or {}
        if "with_runtime.lte" in active_filters and candidates:
            def load_runtime(movie: dict) -> dict:
                detail = self._get(f"/movie/{movie['id']}", {})
                return {**movie, "runtime": detail.get("runtime")}

            with ThreadPoolExecutor(max_workers=min(8, len(candidates))) as executor:
                candidates = list(executor.map(load_runtime, candidates))

        return [
            movie for movie in candidates if self._matches_filters(movie, active_filters)
        ][:count]

    @staticmethod
    def _matches_filters(movie: dict, filters: dict[str, str | int | float]) -> bool:
        rating = float(movie.get("rating") or 0)
        year = movie.get("release_year")
        if "vote_average.gte" in filters and rating < float(filters["vote_average.gte"]):
            return False
        if "vote_average.lte" in filters and rating > float(filters["vote_average.lte"]):
            return False
        if "primary_release_date.gte" in filters:
            minimum_year = int(str(filters["primary_release_date.gte"])[:4])
            if year is None or int(year) < minimum_year:
                return False
        if "primary_release_date.lte" in filters:
            maximum_year = int(str(filters["primary_release_date.lte"])[:4])
            if year is None or int(year) > maximum_year:
                return False
        if "with_runtime.lte" in filters:
            runtime = movie.get("runtime")
            if runtime is None or int(runtime) > int(filters["with_runtime.lte"]):
                return False
        return True

    def get_movie_details(self, movie_id: int) -> dict:
        """영화 상세 정보와 재생 가능한 공식 YouTube 예고편을 반환한다."""
        item = self._get(
            f"/movie/{movie_id}",
            {
                "append_to_response": "videos",
                "include_video_language": "ko,en,null",
            },
        )
        videos = (item.get("videos") or {}).get("results", [])
        trailers = [
            video
            for video in videos
            if video.get("site") == "YouTube" and video.get("type") == "Trailer"
        ]
        trailer = next((video for video in trailers if video.get("official")), None)
        trailer = trailer or (trailers[0] if trailers else None)
        release_date = item.get("release_date") or None
        return {
            "id": item["id"],
            "title": item.get("title") or item.get("original_title") or "제목 미상",
            "overview": item.get("overview") or "",
            "poster_url": f"{_POSTER_BASE_URL}{item['poster_path']}" if item.get("poster_path") else None,
            "backdrop_url": f"{_BACKDROP_BASE_URL}{item['backdrop_path']}" if item.get("backdrop_path") else None,
            "release_year": int(release_date[:4]) if release_date and len(release_date) >= 4 else None,
            "release_date": release_date,
            "runtime": item.get("runtime"),
            "rating": item.get("vote_average") or 0,
            "genres": [genre["name"] for genre in item.get("genres", []) if genre.get("name")],
            "tagline": item.get("tagline") or None,
            "trailer_url": f"https://www.youtube.com/embed/{trailer['key']}" if trailer and trailer.get("key") else None,
        }

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
