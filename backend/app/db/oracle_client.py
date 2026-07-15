"""python-oracledb(Thin 모드) 커넥션 풀과 SQLAlchemy engine/session을 관리한다.

- 원시 SQL(NL2SQL 조회용)은 get_connection()의 raw 커넥션을 사용한다.
- ORM 모델(user_taste_profile 등) 조회는 get_session()을 사용한다.
- 이 모듈 밖에서 oracledb.connect()나 create_engine()을 직접 호출하지 않는다.
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

import oracledb
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

load_dotenv()


class OracleConnectionError(Exception):
    """Oracle 커넥션 풀 생성/획득 실패 시 발생한다."""


def _dsn() -> str:
    host = os.getenv("ORACLE_HOST", "")
    port = os.getenv("ORACLE_PORT", "1521")
    service_name = os.getenv("ORACLE_SERVICE_NAME", "")
    return oracledb.makedsn(host, port, service_name=service_name)


def _sqlalchemy_url() -> str:
    user = os.getenv("ORACLE_USER", "")
    password = os.getenv("ORACLE_PASSWORD", "")
    host = os.getenv("ORACLE_HOST", "")
    port = os.getenv("ORACLE_PORT", "1521")
    service_name = os.getenv("ORACLE_SERVICE_NAME", "")
    return f"oracle+oracledb://{user}:{password}@{host}:{port}/?service_name={service_name}"


_pool: oracledb.ConnectionPool | None = None
_engine = None
_SessionLocal: sessionmaker | None = None


def _get_pool() -> oracledb.ConnectionPool:
    global _pool
    if _pool is None:
        try:
            _pool = oracledb.create_pool(
                user=os.getenv("ORACLE_USER", ""),
                password=os.getenv("ORACLE_PASSWORD", ""),
                dsn=_dsn(),
                min=int(os.getenv("ORACLE_POOL_MIN", "1")),
                max=int(os.getenv("ORACLE_POOL_MAX", "3")),
                increment=1,
            )
        except oracledb.Error as exc:
            raise OracleConnectionError(f"Oracle 커넥션 풀 생성 실패: {exc}") from exc
    return _pool


def _get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        _engine = create_engine(
            _sqlalchemy_url(),
            pool_pre_ping=True,
            pool_size=int(os.getenv("SQLALCHEMY_POOL_SIZE", "3")),
            max_overflow=int(os.getenv("SQLALCHEMY_MAX_OVERFLOW", "2")),
        )
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)
    return _engine


@contextmanager
def get_connection() -> Iterator[oracledb.Connection]:
    """NL2SQL 등 원시 SQL 실행용 커넥션 컨텍스트 매니저."""
    pool = _get_pool()
    try:
        conn = pool.acquire()
    except oracledb.Error as exc:
        raise OracleConnectionError(f"Oracle 커넥션 획득 실패: {exc}") from exc
    try:
        yield conn
    finally:
        pool.release(conn)


@contextmanager
def get_session() -> Iterator[Session]:
    """ORM 모델(repositories/) 조회용 세션 컨텍스트 매니저."""
    _get_engine()
    assert _SessionLocal is not None
    session = _SessionLocal()
    try:
        yield session
    finally:
        session.close()


def check_connection() -> None:
    """/health/db 에서 사용. 연결 실패 시 OracleConnectionError를 던진다."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM DUAL")
        cursor.fetchone()
