import hashlib
import json

from sqlalchemy import func

from app.core.preferences import PREFERRED_GENRE_MIN_WEIGHT, updated_genre_weight
from app.db.models import (
    ConversationSignal,
    Interaction,
    Item,
    OnboardingSignal,
    User,
    UserTasteProfile,
)
from app.db.oracle_client import get_session


def _loads(value: str | None) -> dict:
    if not value:
        return {}
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return {}


def get_or_create_user(visitor_token: str) -> User:
    with get_session() as session:
        user = session.query(User).filter(User.visitor_token == visitor_token).first()
        if user is None:
            user = User(visitor_token=visitor_token)
            session.add(user)
            session.commit()
            session.refresh(user)
        else:
            user.last_seen_at = func.sysdate()
            session.commit()
            session.refresh(user)
        return user


def get_profile_for_user(user_id: int) -> UserTasteProfile | None:
    with get_session() as session:
        return (
            session.query(UserTasteProfile)
            .filter(UserTasteProfile.user_id == user_id)
            .order_by(UserTasteProfile.updated_at.desc())
            .first()
        )


def save_onboarding(
    user_id: int,
    favorite_genres: list[str],
    moods: list[str],
    favorite_movie: str | None,
) -> UserTasteProfile:
    genre_weights = {genre: 1.0 for genre in favorite_genres}
    mood_weights = {mood: 1.0 for mood in moods}
    raw_value = json.dumps(
        {
            "favorite_genres": favorite_genres,
            "moods": moods,
            "favorite_movie": favorite_movie,
        },
        ensure_ascii=False,
    )

    with get_session() as session:
        profile = (
            session.query(UserTasteProfile)
            .filter(UserTasteProfile.user_id == user_id)
            .order_by(UserTasteProfile.updated_at.desc())
            .first()
        )
        if profile is None:
            profile = UserTasteProfile(user_id=user_id)
            session.add(profile)

        profile.genre_weights = json.dumps(genre_weights, ensure_ascii=False)
        profile.mood_weights = json.dumps(mood_weights, ensure_ascii=False)
        profile.confidence_score = 0.45
        profile.updated_at = func.sysdate()
        session.add(
            OnboardingSignal(user_id=user_id, source="fav_item", raw_value=raw_value)
        )
        session.commit()
        session.refresh(profile)
        return profile


def profile_preferences(profile: UserTasteProfile) -> tuple[dict[str, float], dict[str, float]]:
    return _loads(profile.genre_weights), _loads(profile.mood_weights)


def save_feedback(
    user_id: int,
    movie_id: int,
    movie_title: str,
    genres: list[str],
    action: str,
) -> None:
    save_feedback_batch(
        user_id,
        [
            {
                "movie_id": movie_id,
                "movie_title": movie_title,
                "genres": genres,
                "action": action,
            }
        ],
    )


def save_feedback_batch(user_id: int, feedback: list[dict]) -> None:
    with get_session() as session:
        for item in feedback:
            session.add(
                Interaction(
                    user_id=user_id,
                    tmdb_movie_id=item["movie_id"],
                    movie_title=item["movie_title"],
                    movie_genres=",".join(item["genres"]),
                    action=item["action"],
                )
            )

        profile = (
            session.query(UserTasteProfile)
            .filter(UserTasteProfile.user_id == user_id)
            .order_by(UserTasteProfile.updated_at.desc())
            .first()
        )
        if profile is not None:
            weights = _loads(profile.genre_weights)
            scored_feedback = [
                item for item in feedback if item["action"] in {"liked", "disliked"}
            ]
            for item in scored_feedback:
                for genre in item["genres"]:
                    weights[genre] = updated_genre_weight(
                        weights.get(genre),
                        item["action"],
                    )
            profile.genre_weights = json.dumps(weights, ensure_ascii=False)
            current_confidence = float(profile.confidence_score or 0.45)
            profile.confidence_score = min(
                0.95,
                current_confidence + (0.03 * len(scored_feedback)),
            )
            profile.updated_at = func.sysdate()

        session.commit()


def save_conversation_genre_preference(
    user_id: int,
    session_id: str,
    genre: str,
    raw_snippet: str,
) -> float:
    """대화에서 직접 요청한 장르를 약한 장기 취향 신호로 누적한다."""
    with get_session() as session:
        profile = (
            session.query(UserTasteProfile)
            .filter(UserTasteProfile.user_id == user_id)
            .order_by(UserTasteProfile.updated_at.desc())
            .first()
        )
        if profile is None:
            return 0.0

        weights = _loads(profile.genre_weights)
        current_weight = float(weights.get(genre, 0.0))
        updated_weight = round(
            min(2.0, max(PREFERRED_GENRE_MIN_WEIGHT, current_weight + 0.12)),
            3,
        )
        weights[genre] = updated_weight
        profile.genre_weights = json.dumps(weights, ensure_ascii=False)
        profile.updated_at = func.sysdate()
        session.add(
            ConversationSignal(
                session_id=session_id[:50],
                extracted_preference=json.dumps(
                    {
                        "type": "movie_genre_request",
                        "genre": genre,
                        "weight_delta": 0.12,
                    },
                    ensure_ascii=False,
                ),
                raw_snippet=raw_snippet[:2000],
            )
        )
        session.commit()
        return updated_weight


def save_conversation_genre_dislike(
    user_id: int,
    session_id: str,
    genre: str,
    raw_snippet: str,
) -> float:
    """사용자가 '싫어/별로'라고 명시한 장르만 약한 장기 비선호로 저장한다."""
    with get_session() as session:
        profile = (
            session.query(UserTasteProfile)
            .filter(UserTasteProfile.user_id == user_id)
            .order_by(UserTasteProfile.updated_at.desc())
            .first()
        )
        if profile is None:
            return 0.0

        weights = _loads(profile.genre_weights)
        current_weight = float(weights.get(genre, 0.0))
        updated_weight = round(max(-2.0, min(-0.12, current_weight - 0.18)), 3)
        weights[genre] = updated_weight
        profile.genre_weights = json.dumps(weights, ensure_ascii=False)
        profile.updated_at = func.sysdate()
        session.add(
            ConversationSignal(
                session_id=session_id[:50],
                extracted_preference=json.dumps(
                    {
                        "type": "movie_genre_dislike",
                        "genre": genre,
                        "weight_delta": -0.18,
                    },
                    ensure_ascii=False,
                ),
                raw_snippet=raw_snippet[:2000],
            )
        )
        session.commit()
        return updated_weight


def feedback_movie_ids(user_id: int) -> set[int]:
    with get_session() as session:
        rows = (
            session.query(Interaction.tmdb_movie_id)
            .filter(
                Interaction.user_id == user_id,
                Interaction.tmdb_movie_id.isnot(None),
            )
            .all()
        )
        return {int(row[0]) for row in rows}


def liked_movies_for_user(user_id: int, limit: int = 30) -> list[dict]:
    """영화별 가장 최근 평가가 liked인 항목만 최신순으로 반환한다."""
    with get_session() as session:
        rows = (
            session.query(Interaction)
            .filter(
                Interaction.user_id == user_id,
                Interaction.tmdb_movie_id.isnot(None),
            )
            .order_by(Interaction.id.desc())
            .all()
        )
        seen_ids: set[int] = set()
        liked: list[dict] = []
        for row in rows:
            movie_id = int(row.tmdb_movie_id)
            if movie_id in seen_ids:
                continue
            seen_ids.add(movie_id)
            if row.action != "liked":
                continue
            liked.append(
                {
                    "id": movie_id,
                    "title": row.movie_title or "제목 미상",
                    "genres": [
                        genre.strip()
                        for genre in (row.movie_genres or "").split(",")
                        if genre.strip()
                    ],
                }
            )
            if len(liked) >= limit:
                break
        return liked


def _book_external_id(book: dict) -> str:
    isbn = "".join(character for character in str(book.get("isbn") or "").upper() if character.isdigit() or character == "X")
    if isbn:
        return f"isbn:{isbn}"[:50]
    identity = f"{book.get('title', '')}|{book.get('author', '')}".casefold().encode("utf-8")
    return f"book:{hashlib.sha256(identity).hexdigest()[:40]}"


def save_book_feedback(user_id: int, book: dict, action: str) -> None:
    external_id = _book_external_id(book)
    with get_session() as session:
        item = (
            session.query(Item)
            .filter(Item.item_type == "book", Item.external_id == external_id)
            .first()
        )
        metadata = json.dumps(book, ensure_ascii=False)
        if item is None:
            item = Item(
                item_type="book",
                title=str(book.get("title") or "제목 미상")[:200],
                external_id=external_id,
                item_metadata=metadata,
                tags=str(book.get("genre") or "")[:500],
            )
            session.add(item)
            session.flush()
        else:
            item.title = str(book.get("title") or item.title or "제목 미상")[:200]
            item.item_metadata = metadata
            item.tags = str(book.get("genre") or item.tags or "")[:500]
        session.add(Interaction(user_id=user_id, item_id=item.id, action=action))
        session.commit()


def liked_books_for_user(user_id: int, limit: int = 50) -> list[dict]:
    """책별 가장 최근 평가가 liked인 항목만 최신순으로 반환한다."""
    with get_session() as session:
        rows = (
            session.query(Interaction, Item)
            .join(Item, Interaction.item_id == Item.id)
            .filter(Interaction.user_id == user_id, Item.item_type == "book")
            .order_by(Interaction.id.desc())
            .all()
        )
        seen_item_ids: set[int] = set()
        liked: list[dict] = []
        for interaction, item in rows:
            if item.id in seen_item_ids:
                continue
            seen_item_ids.add(item.id)
            if interaction.action != "liked":
                continue
            try:
                book = json.loads(item.item_metadata or "{}")
            except (TypeError, json.JSONDecodeError):
                book = {}
            book["title"] = book.get("title") or item.title or "제목 미상"
            book.setdefault("sources", [])
            liked.append(book)
            if len(liked) >= limit:
                break
        return liked
