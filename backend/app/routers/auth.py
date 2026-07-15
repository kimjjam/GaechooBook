import os

from fastapi import APIRouter, Header, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from app.core.security import (
    CSRF_COOKIE_NAME,
    SESSION_COOKIE_NAME,
    hash_password,
    session_cookie,
    validate_new_password,
    verify_csrf,
)
from app.db.oracle_client import OracleConnectionError
from app.repositories.auth_repo import (
    AccountLockedError,
    DuplicateEmailError,
    InvalidCredentialsError,
    authenticate_account,
    create_auth_session,
    get_auth_context,
    register_account,
    revoke_session,
)
from app.schemas.auth import AuthResponse, AuthUser, LoginRequest, LogoutResponse, RegisterRequest

router = APIRouter(prefix="/auth", tags=["auth"])


def _cookie_secure() -> bool:
    return os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"


def _cookie_samesite() -> str:
    value = os.getenv("SESSION_COOKIE_SAMESITE", "lax").lower()
    return value if value in {"lax", "strict", "none"} else "lax"


def _session_ttl_days() -> int:
    return max(1, min(30, int(os.getenv("SESSION_TTL_DAYS", "14"))))


def _set_session_cookie(response: Response, token: str, csrf_token: str, max_age: int) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=max_age,
        httponly=True,
        secure=_cookie_secure(),
        samesite=_cookie_samesite(),
        path="/",
    )
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=csrf_token,
        max_age=max_age,
        httponly=False,
        secure=_cookie_secure(),
        samesite=_cookie_samesite(),
        path="/",
    )
    response.headers["Cache-Control"] = "no-store"


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        httponly=True,
        secure=_cookie_secure(),
        samesite=_cookie_samesite(),
        path="/",
    )
    response.delete_cookie(
        key=CSRF_COOKIE_NAME,
        httponly=False,
        secure=_cookie_secure(),
        samesite=_cookie_samesite(),
        path="/",
    )


def _auth_response(user, csrf_token: str) -> AuthResponse:
    return AuthResponse(
        user=AuthUser(id=user.id, email=user.email, nickname=user.nickname),
        csrf_token=csrf_token,
    )


@router.post("/register", response_model=AuthResponse, status_code=201)
def register(request: RegisterRequest, response: Response) -> AuthResponse:
    validate_new_password(request.password, str(request.email))
    try:
        user = register_account(
            request.visitor_token,
            str(request.email),
            request.nickname,
            hash_password(request.password),
        )
        new_session = create_auth_session(user.id, _session_ttl_days())
        _set_session_cookie(
            response, new_session.token, new_session.csrf_token, new_session.expires_in_seconds
        )
        return _auth_response(new_session.user, new_session.csrf_token)
    except DuplicateEmailError as exc:
        raise HTTPException(status_code=409, detail="이미 가입된 이메일입니다.") from exc
    except OracleConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/login", response_model=AuthResponse)
def login(request: LoginRequest, response: Response) -> AuthResponse:
    try:
        user = authenticate_account(str(request.email), request.password)
        new_session = create_auth_session(user.id, _session_ttl_days())
        _set_session_cookie(
            response, new_session.token, new_session.csrf_token, new_session.expires_in_seconds
        )
        return _auth_response(new_session.user, new_session.csrf_token)
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 올바르지 않습니다.") from exc
    except AccountLockedError as exc:
        raise HTTPException(status_code=429, detail="로그인 시도가 많아 15분간 잠겼습니다.") from exc
    except OracleConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/session", response_model=AuthResponse | None)
def session(request: Request, response: Response):
    raw_token = session_cookie(request)
    context = get_auth_context(raw_token) if raw_token else None
    if context is None:
        anonymous = JSONResponse(status_code=200, content=None)
        _clear_session_cookie(anonymous)
        anonymous.headers["Cache-Control"] = "no-store"
        return anonymous
    response.headers["Cache-Control"] = "no-store"
    csrf_token = request.cookies.get(CSRF_COOKIE_NAME)
    try:
        verify_csrf(csrf_token, context.csrf_hash)
    except HTTPException:
        new_session = create_auth_session(context.user.id, _session_ttl_days())
        revoke_session(raw_token)
        _set_session_cookie(
            response, new_session.token, new_session.csrf_token, new_session.expires_in_seconds
        )
        return _auth_response(new_session.user, new_session.csrf_token)
    return _auth_response(context.user, csrf_token)


@router.post("/logout", response_model=LogoutResponse)
def logout(
    request: Request,
    response: Response,
    x_csrf_token: str | None = Header(default=None),
) -> LogoutResponse:
    raw_token = session_cookie(request)
    if raw_token:
        context = get_auth_context(raw_token)
        if context is not None:
            verify_csrf(x_csrf_token, context.csrf_hash)
        revoke_session(raw_token)
    _clear_session_cookie(response)
    response.headers["Cache-Control"] = "no-store"
    return LogoutResponse(logged_out=True)
