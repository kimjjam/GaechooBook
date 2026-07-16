from concurrent.futures import ThreadPoolExecutor

import httpx
from fastapi import APIRouter, Header, HTTPException, Query, Request

from app.api_clients.tmdb import TMDBClient
from app.core.preferences import preferred_genres
from app.core.scoring.recommendation import rank_movies
from app.core.security import session_cookie, verify_csrf
from app.db.oracle_client import OracleConnectionError
from app.repositories.personalization_repo import (
    feedback_movie_ids,
    get_or_create_user,
    get_profile_for_user,
    liked_movies_for_user,
    profile_preferences,
    save_feedback,
    save_feedback_batch,
    save_onboarding,
)
from app.repositories.auth_repo import get_auth_context
from app.schemas.personalization import (
    FeedbackBatchRequest,
    FeedbackBatchResponse,
    FeedbackRequest,
    FeedbackResponse,
    MovieDetailResponse,
    MovieRecommendation,
    OnboardingRequest,
    ProfileResponse,
    RecommendationResponse,
)

router = APIRouter(prefix="/personalization", tags=["personalization"])


def _resolve_user(
    http_request: Request,
    visitor_token: str,
    csrf_token: str | None = None,
    require_csrf: bool = False,
):
    raw_token = session_cookie(http_request)
    if raw_token:
        context = get_auth_context(raw_token)
        if context is None:
            raise HTTPException(status_code=401, detail="로그인 세션이 만료되었습니다.")
        if require_csrf:
            verify_csrf(csrf_token, context.csrf_hash)
        return context.user
    return get_or_create_user(visitor_token)


def _profile_response(visitor_token: str, user) -> ProfileResponse:
    profile = get_profile_for_user(user.id)
    if profile is None:
        return ProfileResponse(visitor_token=visitor_token, onboarding_completed=False)
    genres, moods = profile_preferences(profile)
    return ProfileResponse(
        visitor_token=visitor_token,
        onboarding_completed=True,
        favorite_genres=preferred_genres(genres),
        moods=list(moods.keys()),
    )


@router.get("/profile", response_model=ProfileResponse)
def get_profile(
    http_request: Request,
    visitor_token: str = Header(alias="X-Visitor-Token"),
) -> ProfileResponse:
    if not 8 <= len(visitor_token) <= 64:
        raise HTTPException(status_code=422, detail="잘못된 방문자 토큰입니다.")
    try:
        user = _resolve_user(http_request, visitor_token)
        return _profile_response(visitor_token, user)
    except OracleConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/onboarding", response_model=ProfileResponse)
def complete_onboarding(
    request: OnboardingRequest,
    http_request: Request,
    x_csrf_token: str | None = Header(default=None),
) -> ProfileResponse:
    try:
        user = _resolve_user(
            http_request,
            request.visitor_token,
            x_csrf_token,
            require_csrf=True,
        )
        save_onboarding(
            user.id,
            request.favorite_genres,
            request.moods,
            request.favorite_movie,
        )
        return _profile_response(request.visitor_token, user)
    except OracleConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/recommendations", response_model=RecommendationResponse)
def get_recommendations(
    http_request: Request,
    visitor_token: str = Header(alias="X-Visitor-Token"),
    limit: int = Query(default=10, ge=1, le=60),
    exclude_movie_ids: str = Query(default="", max_length=6000),
) -> RecommendationResponse:
    try:
        user = _resolve_user(http_request, visitor_token)
        profile = get_profile_for_user(user.id)
        if profile is None:
            raise HTTPException(status_code=409, detail="먼저 취향 설정을 완료해 주세요.")
        genres, moods = profile_preferences(profile)
        active_genres = preferred_genres(genres)
        primary_genres = sorted(
            active_genres,
            key=lambda genre: float(genres.get(genre, 0)),
            reverse=True,
        )[:2]
        requested_exclusions = {
            int(value)
            for value in exclude_movie_ids.split(",")
            if value.strip().isdigit()
        }
        saved_exclusions = feedback_movie_ids(user.id)
        all_exclusions = saved_exclusions | requested_exclusions
        diversity_seed = f"{user.id}:{','.join(map(str, sorted(all_exclusions)))}"
        client = TMDBClient()
        candidates = client.discover_for_genres(
            primary_genres,
            count=80,
            diversity_seed=diversity_seed,
            excluded_ids=all_exclusions,
            require_all_genres=len(primary_genres) > 1,
        )
        ranked = rank_movies(
            candidates,
            genres,
            moods,
            all_exclusions,
            limit,
            confidence=float(profile.confidence_score or 0.45),
        )
        if len(ranked) < limit and len(primary_genres) > 1:
            ranked_ids = {int(movie["id"]) for movie in ranked}
            partial_match_exclusions = all_exclusions | ranked_ids
            partial_match_candidates = client.discover_for_genres(
                primary_genres,
                count=80,
                diversity_seed=f"{diversity_seed}:any-preferred-genre",
                excluded_ids=partial_match_exclusions,
                require_all_genres=False,
            )
            ranked.extend(
                rank_movies(
                    partial_match_candidates,
                    genres,
                    moods,
                    partial_match_exclusions,
                    limit - len(ranked),
                    confidence=float(profile.confidence_score or 0.45),
                )
            )
        if len(ranked) < limit and set(active_genres) != set(primary_genres):
            ranked_ids = {int(movie["id"]) for movie in ranked}
            preferred_exclusions = all_exclusions | ranked_ids
            preferred_candidates = client.discover_for_genres(
                active_genres,
                count=80,
                diversity_seed=f"{diversity_seed}:other-preferred-genres",
                excluded_ids=preferred_exclusions,
                require_all_genres=False,
            )
            ranked.extend(
                rank_movies(
                    preferred_candidates,
                    genres,
                    moods,
                    preferred_exclusions,
                    limit - len(ranked),
                    confidence=float(profile.confidence_score or 0.45),
                )
            )
        if len(ranked) < limit:
            ranked_ids = {int(movie["id"]) for movie in ranked}
            catalog_exclusions = all_exclusions | ranked_ids
            catalog_candidates = client.discover_for_genres(
                [],
                count=80,
                diversity_seed=f"{diversity_seed}:all-catalog",
                excluded_ids=catalog_exclusions,
                require_all_genres=False,
            )
            ranked.extend(
                rank_movies(
                    catalog_candidates,
                    genres,
                    moods,
                    catalog_exclusions,
                    limit - len(ranked),
                    confidence=float(profile.confidence_score or 0.45),
                )
            )
        return RecommendationResponse(
            recommendations=[MovieRecommendation(**movie) for movie in ranked]
        )
    except OracleConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/liked-movies", response_model=RecommendationResponse)
def get_liked_movies(
    http_request: Request,
    visitor_token: str = Header(alias="X-Visitor-Token"),
    limit: int = Query(default=30, ge=1, le=50),
) -> RecommendationResponse:
    try:
        user = _resolve_user(http_request, visitor_token)
        saved_movies = liked_movies_for_user(user.id, limit)
        client = TMDBClient()

        def hydrate(movie: dict) -> dict:
            try:
                details = client.get_movie_details(movie["id"])
                return {
                    **details,
                    "score": 1.0,
                    "reason": "좋아요한 영화",
                }
            except (httpx.HTTPError, RuntimeError, KeyError):
                return {
                    **movie,
                    "overview": "",
                    "poster_url": None,
                    "release_year": None,
                    "rating": 0,
                    "score": 1.0,
                    "reason": "좋아요한 영화",
                }

        if not saved_movies:
            return RecommendationResponse(recommendations=[])
        with ThreadPoolExecutor(max_workers=min(8, len(saved_movies))) as executor:
            hydrated = list(executor.map(hydrate, saved_movies))
        return RecommendationResponse(
            recommendations=[MovieRecommendation(**movie) for movie in hydrated]
        )
    except OracleConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/movies/{movie_id}", response_model=MovieDetailResponse)
def get_movie_detail(movie_id: int) -> MovieDetailResponse:
    try:
        return MovieDetailResponse(**TMDBClient().get_movie_details(movie_id))
    except httpx.HTTPStatusError as exc:
        status_code = 404 if exc.response.status_code == 404 else 503
        raise HTTPException(status_code=status_code, detail="영화 상세 정보를 불러오지 못했습니다.") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="영화 상세 정보 제공자에 연결하지 못했습니다.") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/feedback", response_model=FeedbackResponse)
def record_feedback(
    request: FeedbackRequest,
    http_request: Request,
    x_csrf_token: str | None = Header(default=None),
) -> FeedbackResponse:
    try:
        user = _resolve_user(
            http_request,
            request.visitor_token,
            x_csrf_token,
            require_csrf=True,
        )
        if get_profile_for_user(user.id) is None:
            raise HTTPException(status_code=409, detail="먼저 취향 설정을 완료해 주세요.")
        save_feedback(
            user.id,
            request.movie_id,
            request.movie_title,
            request.genres,
            request.action,
        )
        return FeedbackResponse(saved=True, message="다음 추천에 취향을 반영할게요.")
    except OracleConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/feedback/batch", response_model=FeedbackBatchResponse)
def record_feedback_batch(
    request: FeedbackBatchRequest,
    http_request: Request,
    x_csrf_token: str | None = Header(default=None),
) -> FeedbackBatchResponse:
    try:
        user = _resolve_user(
            http_request,
            request.visitor_token,
            x_csrf_token,
            require_csrf=True,
        )
        if get_profile_for_user(user.id) is None:
            raise HTTPException(status_code=409, detail="먼저 취향 설정을 완료해 주세요.")
        save_feedback_batch(
            user.id,
            [item.model_dump() for item in request.feedback],
        )
        return FeedbackBatchResponse(
            saved_count=len(request.feedback),
            message="평가를 저장하고 다음 추천에 반영할게요.",
        )
    except OracleConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
