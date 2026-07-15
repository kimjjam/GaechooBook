from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from app.core.security import (
    AuthContext,
    hash_secret,
    new_secret,
    normalize_email,
    utc_now,
    verify_password,
)
from app.db.models import AuthSession, User
from app.db.oracle_client import get_session


class DuplicateEmailError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class AccountLockedError(Exception):
    pass


@dataclass(frozen=True)
class NewSession:
    user: User
    token: str
    csrf_token: str
    expires_in_seconds: int


def register_account(
    visitor_token: str,
    email: str,
    nickname: str,
    encoded_password: str,
) -> User:
    normalized = normalize_email(email)
    with get_session() as session:
        if session.query(User.id).filter(func.lower(User.email) == normalized).first():
            raise DuplicateEmailError
        user = session.query(User).filter(User.visitor_token == visitor_token).first()
        if user is None:
            user = User(visitor_token=visitor_token)
            session.add(user)
        user.email = normalized
        # 익명 토큰으로 계정 데이터에 다시 접근하지 못하도록 계정 승격 즉시 분리한다.
        user.visitor_token = None
        user.nickname = nickname.strip()
        user.password_hash = encoded_password
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = func.sysdate()
        try:
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            raise DuplicateEmailError from exc
        session.refresh(user)
        return user


def authenticate_account(email: str, password: str) -> User:
    normalized = normalize_email(email)
    with get_session() as session:
        user = session.query(User).filter(func.lower(User.email) == normalized).first()
        password_valid = verify_password(password, user.password_hash if user else None)
        if user is None:
            raise InvalidCredentialsError

        now = utc_now()
        if user.locked_until is not None and user.locked_until > now:
            raise AccountLockedError
        if not password_valid:
            attempts = int(user.failed_login_attempts or 0) + 1
            user.failed_login_attempts = attempts
            if attempts >= 5:
                user.locked_until = now + timedelta(minutes=15)
                user.failed_login_attempts = 0
            session.commit()
            raise InvalidCredentialsError

        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = func.sysdate()
        session.commit()
        session.refresh(user)
        return user


def create_auth_session(user_id: int, ttl_days: int) -> NewSession:
    token = new_secret()
    csrf_token = new_secret()
    ttl_seconds = ttl_days * 24 * 60 * 60
    expires_at = utc_now() + timedelta(seconds=ttl_seconds)
    with get_session() as session:
        session.query(AuthSession).filter(AuthSession.expires_at <= utc_now()).delete(
            synchronize_session=False
        )
        existing_sessions = (
            session.query(AuthSession)
            .filter(AuthSession.user_id == user_id)
            .order_by(AuthSession.created_at.desc())
            .all()
        )
        for stale_session in existing_sessions[4:]:
            session.delete(stale_session)
        session.add(
            AuthSession(
                user_id=user_id,
                token_hash=hash_secret(token),
                csrf_hash=hash_secret(csrf_token),
                expires_at=expires_at,
            )
        )
        session.commit()
        user = session.get(User, user_id)
        assert user is not None
        session.refresh(user)
        return NewSession(user=user, token=token, csrf_token=csrf_token, expires_in_seconds=ttl_seconds)


def get_auth_context(raw_token: str) -> AuthContext | None:
    token_hash = hash_secret(raw_token)
    with get_session() as session:
        auth_session = (
            session.query(AuthSession)
            .filter(AuthSession.token_hash == token_hash)
            .first()
        )
        if auth_session is None:
            return None
        if auth_session.expires_at <= utc_now():
            session.delete(auth_session)
            session.commit()
            return None
        user = session.get(User, auth_session.user_id)
        if user is None or not user.email:
            return None
        auth_session.last_used_at = func.sysdate()
        session.commit()
        session.refresh(user)
        return AuthContext(user=user, csrf_hash=auth_session.csrf_hash, token_hash=token_hash)


def revoke_session(raw_token: str) -> None:
    with get_session() as session:
        session.query(AuthSession).filter(AuthSession.token_hash == hash_secret(raw_token)).delete(
            synchronize_session=False
        )
        session.commit()
