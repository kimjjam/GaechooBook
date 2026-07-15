"""발화 수신 → 분류 → 라우팅. 각 intent의 실제 처리 로직은 스텁이며,
2~5단계에서 core/scoring, nl2sql, visualize 파이프라인으로 교체된다.
"""
from fastapi import APIRouter, HTTPException, Request

from app.api_clients.book_search import search_books
from app.api_clients.tmdb import TMDBClient
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


def _extract_genre_keyword(message: str) -> str | None:
    for keyword in _GENRE_KEYWORDS:
        if keyword in message:
            return keyword
    return None


def _extract_book_query(message: str, genre: str | None) -> str:
    query = message
    for phrase in _BOOK_QUERY_NOISE:
        query = query.replace(phrase, " ")
    query = " ".join(query.split()).strip(" ?!.,")
    return query if len(query) >= 2 else (genre or "베스트셀러")


def _handle_recommend(
    message: str,
    session_id: str,
    authenticated_user: User | None = None,
) -> ChatResponse:
    genre = _extract_genre_keyword(message)
    wants_books = any(keyword in message for keyword in _BOOK_KEYWORDS)

    try:
        if wants_books:
            book_query = _extract_book_query(message, genre)
            search_result = search_books(book_query, size_per_provider=5, limit=6)
            books = search_result.books
            if not books:
                failed = ", ".join(search_result.failed_providers)
                detail = f" 응답하지 않은 제공자: {failed}." if failed else ""
                return ChatResponse(
                    intent=Intent.RECOMMEND,
                    reply=f"'{book_query}' 도서를 찾지 못했어요.{detail}",
                    data={
                        "query": book_query,
                        "books": [],
                        "providers": search_result.successful_providers,
                        "failed_providers": search_result.failed_providers,
                    },
                )
            lines = []
            for book in books:
                author = book.get("author") or "저자 미상"
                year = f", {book['pub_year']}" if book.get("pub_year") else ""
                sources = " · ".join(book.get("sources", []))
                lines.append(f"- {book['title']} ({author}{year}) [{sources}]")
            data = {
                "query": book_query,
                "books": books,
                "providers": search_result.successful_providers,
                "failed_providers": search_result.failed_providers,
            }
        else:
            user = authenticated_user or get_or_create_user(session_id)
            profile = get_profile_for_user(user.id)
            if profile is None:
                return ChatResponse(intent=Intent.RECOMMEND, reply="먼저 위에서 취향 설정을 완료해 주세요.")
            genres, moods = profile_preferences(profile)
            requested_genres = [genre] if genre else list(genres.keys())
            candidates = TMDBClient().discover_for_genres(requested_genres, count=30)
            movies = rank_movies(
                candidates,
                genres,
                moods,
                feedback_movie_ids(user.id),
                limit=5,
                confidence=float(profile.confidence_score or 0.45),
            )
            if not movies:
                return ChatResponse(intent=Intent.RECOMMEND, reply="새로 추천할 영화를 찾지 못했어요.")
            lines = [f"- {movie['title']} ({movie['release_year']}, 평점 {movie['rating']:.1f})" for movie in movies]
            data = {"movies": movies}
    except OracleConnectionError as exc:
        return ChatResponse(intent=Intent.RECOMMEND, reply=f"DB 연결에 실패해 추천을 가져오지 못했습니다: {exc}")
    except RuntimeError as exc:
        return ChatResponse(intent=Intent.RECOMMEND, reply=f"영화 정보를 가져오지 못했습니다: {exc}")

    if wants_books:
        prefix = f"'{book_query}' 통합 도서 검색 결과예요.\n"
        if data["failed_providers"]:
            prefix += f"(현재 응답하지 않은 제공자: {', '.join(data['failed_providers'])})\n"
    else:
        prefix = "저장된 취향을 반영한 추천이에요.\n"
    reply = prefix + "\n".join(lines)
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
    return _HANDLERS[intent](request.message, request.session_id, authenticated_user)
