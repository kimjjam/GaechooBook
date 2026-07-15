"""제안서 6장 DDL을 그대로 옮긴 SQLAlchemy 모델.

컬럼/제약을 바꿔야 하면 팀 전체와 상의 후 이 파일 한 곳만 수정한다
(CLAUDE_v3_Oracle팀과제.md 5장: 스키마 임의 변경 금지).
CLOB 컬럼은 애플리케이션 레벨에서 JSON 문자열로 파싱/직렬화한다.
"""
from __future__ import annotations

from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKey,
    Identity,
    Integer,
    Numeric,
    String,
    Text,
    TIMESTAMP,
    func,
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, Identity(always=False), primary_key=True)
    visitor_token = Column(String(64), nullable=True, unique=True)
    email = Column(String(320))
    password_hash = Column(String(512))
    nickname = Column(String(50))
    failed_login_attempts = Column(Integer, nullable=False, server_default="0")
    locked_until = Column(TIMESTAMP)
    created_at = Column(TIMESTAMP, server_default=func.sysdate())
    last_seen_at = Column(TIMESTAMP, server_default=func.sysdate())
    last_login_at = Column(TIMESTAMP)


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id = Column(Integer, Identity(always=False), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token_hash = Column(String(64), nullable=False, unique=True)
    csrf_hash = Column(String(64), nullable=False)
    expires_at = Column(TIMESTAMP, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.sysdate())
    last_used_at = Column(TIMESTAMP, server_default=func.sysdate())


class UserTasteProfile(Base):
    __tablename__ = "user_taste_profile"

    id = Column(Integer, Identity(always=False), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    genre_weights = Column(Text)  # JSON 문자열
    mood_weights = Column(Text)  # JSON 문자열
    novelty_pref = Column(Numeric(5, 3))
    intensity_pref = Column(Numeric(5, 3))
    confidence_score = Column(Numeric(5, 3))
    mbti = Column(String(4))
    updated_at = Column(TIMESTAMP, server_default=func.sysdate())


class Item(Base):
    __tablename__ = "items"
    __table_args__ = (CheckConstraint("item_type IN ('movie','book')", name="ck_items_item_type"),)

    id = Column(Integer, Identity(always=False), primary_key=True)
    item_type = Column(String(10), nullable=False)
    title = Column(String(200))
    external_id = Column(String(50))
    # 파이썬의 declarative Base.metadata와 이름이 충돌하므로 속성명만 다르게 매핑
    item_metadata = Column("metadata", Text)  # JSON 문자열
    tags = Column(String(500))


class Interaction(Base):
    __tablename__ = "interactions"
    __table_args__ = (
        CheckConstraint("action IN ('liked','disliked','skipped','watched')", name="ck_interactions_action"),
    )

    id = Column(Integer, Identity(always=False), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    item_id = Column(Integer, ForeignKey("items.id"))
    tmdb_movie_id = Column(Integer)
    movie_title = Column(String(200))
    movie_genres = Column(String(500))
    action = Column(String(10), nullable=False)
    rating = Column(Numeric(5, 3))
    created_at = Column(TIMESTAMP, server_default=func.sysdate())


class OnboardingSignal(Base):
    __tablename__ = "onboarding_signals"
    __table_args__ = (
        CheckConstraint("source IN ('fav_item','swipe','slider','quiz')", name="ck_onboarding_signals_source"),
    )

    id = Column(Integer, Identity(always=False), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    source = Column(String(10), nullable=False)
    raw_value = Column(Text)  # JSON 문자열
    created_at = Column(TIMESTAMP, server_default=func.sysdate())


class ConversationSignal(Base):
    __tablename__ = "conversation_signals"

    id = Column(Integer, Identity(always=False), primary_key=True)
    session_id = Column(String(50))
    extracted_preference = Column(Text)  # JSON 문자열
    raw_snippet = Column(String(2000))
    created_at = Column(TIMESTAMP, server_default=func.sysdate())


class Movie(Base):
    __tablename__ = "movies"

    id = Column(Integer, Identity(always=False), primary_key=True)
    title = Column(String(200))
    release_year = Column(Integer)
    genre = Column(String(100))
    rating = Column(Numeric(4, 2))
    country = Column(String(50))


class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, Identity(always=False), primary_key=True)
    title = Column(String(200))
    author = Column(String(100))
    genre = Column(String(100))
    pub_year = Column(Integer)
