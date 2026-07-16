"""발화 수신 → 분류 → 라우팅. 각 intent의 실제 처리 로직은 스텁이며,
2~5단계에서 core/scoring, nl2sql, visualize 파이프라인으로 교체된다.
"""
import re

from fastapi import APIRouter, HTTPException, Request

from app.api_clients.book_search import search_books
from app.api_clients.tmdb import TMDBClient
from app.core.preferences import preferred_genres
from app.core.recommendation_query import (
    looks_like_recommendation_followup,
    parse_recommendation_query,
)
from app.core.scoring.recommendation import rank_movies
from app.core.security import session_cookie
from app.db.models import User
from app.db.oracle_client import OracleConnectionError
from app.nl2sql.executor import execute_query
from app.nl2sql.generator import generate_sql
from app.nl2sql.validator import SQLValidationError
from app.repositories.personalization_repo import (
    feedback_movie_ids,
    get_or_create_user,
    get_profile_for_user,
    profile_preferences,
    save_conversation_genre_preference,
    save_conversation_genre_dislike,
)
from app.repositories.auth_repo import get_auth_context
from app.routers.classify import classify_utterance
from app.schemas.chat import ChatRequest, ChatResponse, Intent

router = APIRouter()

# movies.genre/books.genre에 실제 존재하는 값과 매칭되는 키워드만 인식한다
# (TMDB 장르표, 카카오 시드 쿼리와 맞춰둔 목록 — 4단계 개인화 스코어링 전까지의 임시 필터).
_GENRE_KEYWORDS = [
    "액션", "모험", "애니메이션", "코미디", "범죄", "다큐멘터리", "드라마", "가족",
    "판타지", "역사", "공포", "음악", "미스터리", "로맨스", "SF", "스릴러", "전쟁", "서부",
    "소설", "에세이", "자기계발", "인문학", "과학",
]
_BOOK_KEYWORDS = ("책", "도서", "소설", "에세이", "자기계발", "인문학")
_BOOK_QUERY_NOISE = (
    "추천해 줘", "추천해줘", "검색해 줘", "검색해줘", "찾아 줘", "찾아줘",
    "보여 줘", "보여줘", "읽고 싶어", "읽고싶어", "읽을 만한", "읽을만한",
    "추천", "검색", "책", "도서",
)
_BOOK_RECOMMENDATION_LIMIT = 5


def _extract_genre_keyword(message: str) -> str | None:
    for keyword in _GENRE_KEYWORDS:
        if keyword in message:
            return keyword
    return None


def _extract_book_query(message: str, genre: str | None) -> str:
    query = message
    for phrase in _BOOK_QUERY_NOISE:
        query = query.replace(phrase, " ")
    query = " ".join(query.split()).strip(" :?!.,")
    return query if len(query) >= 2 else (genre or "베스트셀러")


def _book_identity(book: dict) -> tuple[str, ...]:
    isbn = re.sub(r"[^0-9X]", "", str(book.get("isbn") or "").upper())
    if len(isbn) in (10, 13):
        return ("isbn", isbn)
    title = " ".join(str(book.get("title") or "").casefold().split())
    author = " ".join(str(book.get("author") or "").casefold().split())
    return ("title", title, author)


def _search_recommended_books(book_query: str):
    """취향 문장이 너무 구체적이면 첫 조건으로 한 번 완화해 5권을 채운다."""
    results = [
        search_books(
            book_query,
            size_per_provider=5,
            limit=_BOOK_RECOMMENDATION_LIMIT,
        )
    ]
    if len(results[0].books) < _BOOK_RECOMMENDATION_LIMIT and "," in book_query:
        fallback_query = book_query.split(",", 1)[0].strip()
        if len(fallback_query) >= 2:
            results.append(
                search_books(
                    fallback_query,
                    size_per_provider=5,
                    limit=_BOOK_RECOMMENDATION_LIMIT,
                )
            )

    books: list[dict] = []
    seen: set[tuple[str, ...]] = set()
    for result in results:
        for book in result.books:
            identity = _book_identity(book)
            if identity in seen:
                continue
            seen.add(identity)
            books.append(book)
            if len(books) >= _BOOK_RECOMMENDATION_LIMIT:
                break
        if len(books) >= _BOOK_RECOMMENDATION_LIMIT:
            break

    successful_providers = list(dict.fromkeys(
        provider for result in results for provider in result.successful_providers
    ))
    failed_providers = [
        provider
        for provider in dict.fromkeys(
            provider for result in results for provider in result.failed_providers
        )
        if provider not in successful_providers
    ]
    return books, successful_providers, failed_providers


def _handle_recommend(
    message: str,
    session_id: str,
    authenticated_user: User | None = None,
    recommendation_context: dict | None = None,
    exclude_movie_ids: list[int] | None = None,
) -> ChatResponse:
    genre = _extract_genre_keyword(message)
    wants_books = any(keyword in message for keyword in _BOOK_KEYWORDS)

    try:
        if wants_books:
            book_query = _extract_book_query(message, genre)
            books, successful_providers, failed_providers = _search_recommended_books(book_query)
            if not books:
                failed = ", ".join(failed_providers)
                detail = f" 응답하지 않은 제공자: {failed}." if failed else ""
                return ChatResponse(
                    intent=Intent.RECOMMEND,
                    reply=f"'{book_query}' 도서를 찾지 못했어요.{detail}",
                    data={
                        "query": book_query,
                        "books": [],
                        "providers": successful_providers,
                        "failed_providers": failed_providers,
                    },
                )
            data = {
                "query": book_query,
                "books": books,
                "providers": successful_providers,
                "failed_providers": failed_providers,
            }
        else:
            parsed = parse_recommendation_query(message, recommendation_context)
            query = parsed.query
            if parsed.needs_rating_clarification:
                return ChatResponse(
                    intent=Intent.RECOMMEND,
                    reply="평점이 좋은 작품의 기준을 몇 점으로 할까요? 예: ‘7점 이상’",
                    data={"recommendation_context": query.to_dict(), "needs_clarification": "min_rating"},
                )
            user = authenticated_user or get_or_create_user(session_id)
            profile = get_profile_for_user(user.id)
            if profile is None:
                return ChatResponse(intent=Intent.RECOMMEND, reply="먼저 위에서 취향 설정을 완료해 주세요.")
            genres, moods = profile_preferences(profile)
            learned_from_conversation = False
            for requested_genre in query.genres:
                genres[requested_genre] = save_conversation_genre_preference(
                    user.id, session_id, requested_genre, message,
                )
                learned_from_conversation = True
            for disliked_genre in parsed.durable_dislikes:
                genres[disliked_genre] = save_conversation_genre_dislike(
                    user.id, session_id, disliked_genre, message,
                )
            requested_genres = query.genres or preferred_genres(genres)
            excluded_ids = feedback_movie_ids(user.id) | {
                int(movie_id) for movie_id in (exclude_movie_ids or []) if int(movie_id) > 0
            }
            client = TMDBClient()
            if query.similar_to:
                candidates = client.recommend_similar(
                    query.similar_to,
                    count=80,
                    filters=query.tmdb_filters(),
                )
            else:
                candidates = client.discover_for_genres(
                    requested_genres,
                    count=80,
                    diversity_seed=session_id,
                    filters=query.tmdb_filters(),
                )
            candidates = query.apply(candidates)
            movies = rank_movies(
                candidates,
                genres,
                moods,
                excluded_ids,
                limit=query.limit,
                confidence=float(profile.confidence_score or 0.45),
                requested_genres=query.genres,
                requested_moods=query.moods,
                query_description=query.describe(),
            )
            if query.sort_by == "rating":
                movies.sort(key=lambda item: item.get("rating") or 0, reverse=True)
            elif query.sort_by == "recent":
                movies.sort(key=lambda item: item.get("release_year") or 0, reverse=True)
            if not movies:
                relaxation = []
                if query.min_rating is not None:
                    relaxation.append(f"평점 기준을 {max(0, query.min_rating - 0.5):g}점으로 낮추기")
                if query.max_runtime is not None:
                    relaxation.append(f"러닝타임을 {query.max_runtime + 20}분까지 늘리기")
                suggestion = f" {' 또는 '.join(relaxation)}를 시도해볼까요?" if relaxation else " 조건을 하나 줄여 다시 찾아볼까요?"
                return ChatResponse(
                    intent=Intent.RECOMMEND,
                    reply=f"‘{query.describe()}’ 조건에 맞는 새 영화를 찾지 못했어요.{suggestion}",
                    data={"movies": [], "recommendation_context": query.to_dict()},
                )
            data = {
                "movies": movies,
                "learned_genre": ", ".join(query.genres) if learned_from_conversation else None,
                "recommendation_context": query.to_dict(),
                "applied_filters": query.describe(),
            }
    except OracleConnectionError as exc:
        return ChatResponse(intent=Intent.RECOMMEND, reply=f"DB 연결에 실패해 추천을 가져오지 못했습니다: {exc}")
    except RuntimeError as exc:
        return ChatResponse(intent=Intent.RECOMMEND, reply=f"영화 정보를 가져오지 못했습니다: {exc}")

    if wants_books:
        reply = f"취향을 반영해 책 {len(data['books'])}권을 골랐어요. 카드를 눌러 간단히 살펴보세요."
        if data["failed_providers"]:
            reply += f" 일부 제공자({', '.join(data['failed_providers'])})의 결과는 제외됐어요."
    else:
        reply = f"{data['applied_filters']} 조건과 저장된 취향을 함께 반영했어요. 카드를 누르면 상세 정보와 예고편을 볼 수 있어요."
        if data.get("learned_genre"):
            reply = f"오늘 찾은 {data['learned_genre']} 장르도 가벼운 취향 신호로 기억할게요.\n" + reply
    return ChatResponse(intent=Intent.RECOMMEND, reply=reply, data=data)


def _handle_nl2sql(
    message: str,
    _session_id: str,
    _authenticated_user: User | None = None,
) -> ChatResponse:
    try:
        sql = generate_sql(message)
        rows = execute_query(sql)
    except SQLValidationError as exc:
        return ChatResponse(intent=Intent.NL2SQL, reply=f"안전한 조회로 변환하지 못했습니다: {exc}")
    except OracleConnectionError as exc:
        return ChatResponse(intent=Intent.NL2SQL, reply=f"DB 연결에 실패해 조회하지 못했습니다: {exc}")
    except Exception as exc:  # LLM 응답 파싱 실패 등 예상 밖 오류
        return ChatResponse(intent=Intent.NL2SQL, reply=f"질의를 처리하지 못했습니다: {exc}")

    if not rows:
        return ChatResponse(intent=Intent.NL2SQL, reply="조건에 맞는 결과가 없습니다.", data={"sql": sql, "rows": []})

    preview = rows[:5]
    lines = [", ".join(f"{k}: {v}" for k, v in row.items()) for row in preview]
    reply = f"조회 결과 {len(rows)}건 중 상위 {len(preview)}건:\n" + "\n".join(lines)
    return ChatResponse(intent=Intent.NL2SQL, reply=reply, data={"sql": sql, "rows": preview})


def _handle_visualize(
    message: str,
    _session_id: str,
    _authenticated_user: User | None = None,
) -> ChatResponse:
    return ChatResponse(intent=Intent.VISUALIZE, reply="(스텁) 시각화 파이프라인은 5단계에서 연결됩니다.")


def _handle_chitchat(
    message: str,
    _session_id: str,
    _authenticated_user: User | None = None,
) -> ChatResponse:
    return ChatResponse(intent=Intent.CHITCHAT, reply="무드픽입니다. 영화 추천이나 데이터 질의를 해보세요.")


_HANDLERS = {
    Intent.RECOMMEND: _handle_recommend,
    Intent.NL2SQL: _handle_nl2sql,
    Intent.VISUALIZE: _handle_visualize,
    Intent.CHITCHAT: _handle_chitchat,
}


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, http_request: Request) -> ChatResponse:
    authenticated_user = None
    raw_token = session_cookie(http_request)
    if raw_token:
        context = get_auth_context(raw_token)
        if context is None:
            raise HTTPException(status_code=401, detail="로그인 세션이 만료되었습니다.")
        authenticated_user = context.user
    intent = classify_utterance(request.message)
    if (
        intent in {Intent.CHITCHAT, Intent.NL2SQL}
        and request.recommendation_context
        and looks_like_recommendation_followup(request.message)
    ):
        intent = Intent.RECOMMEND
    if intent == Intent.RECOMMEND:
        return _handle_recommend(
            request.message,
            request.session_id,
            authenticated_user,
            request.recommendation_context,
            request.exclude_movie_ids,
        )
    return _HANDLERS[intent](request.message, request.session_id, authenticated_user)
