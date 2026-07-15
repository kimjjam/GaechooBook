import hashlib
import os
import secrets
from dataclasses import dataclass
from datetime import datetime

from fastapi import HTTPException, Request
from pwdlib import PasswordHash

from app.db.models import User

password_hash = PasswordHash.recommended()
_DUMMY_HASH = password_hash.hash("not-a-real-password-for-timing-only")
SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "moodpick_session")
CSRF_COOKIE_NAME = os.getenv("CSRF_COOKIE_NAME", "moodpick_csrf")

_COMMON_PASSWORDS = {
    "123456789012",
    "password1234",
    "qwerty123456",
    "iloveyou1234",
    "admin12345678",
}


@dataclass(frozen=True)
class AuthContext:
    user: User
    csrf_hash: str
    token_hash: str


def normalize_email(email: str) -> str:
    return email.strip().casefold()


def validate_new_password(password: str, email: str) -> None:
    if len(password) < 12:
        raise HTTPException(status_code=422, detail="비밀번호는 12자 이상이어야 합니다.")
    if len(password) > 128:
        raise HTTPException(status_code=422, detail="비밀번호는 128자 이하여야 합니다.")
    lowered = password.casefold()
    local_part = normalize_email(email).split("@", 1)[0]
    if lowered in _COMMON_PASSWORDS or (len(local_part) >= 4 and local_part in lowered):
        raise HTTPException(status_code=422, detail="이메일과 무관한 더 긴 비밀번호를 사용해 주세요.")


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, stored_hash: str | None) -> bool:
    return password_hash.verify(password, stored_hash or _DUMMY_HASH)


def new_secret() -> str:
    return secrets.token_urlsafe(32)


def hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def utc_now() -> datetime:
    return datetime.utcnow()


def verify_csrf(csrf_token: str | None, expected_hash: str) -> None:
    if not csrf_token or not secrets.compare_digest(hash_secret(csrf_token), expected_hash):
        raise HTTPException(status_code=403, detail="요청 보안 토큰이 올바르지 않습니다.")


def session_cookie(request: Request) -> str | None:
    return request.cookies.get(SESSION_COOKIE_NAME)
