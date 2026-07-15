"""Oracle connection pool and SQLAlchemy session management.

Local development uses ``ORACLE_HOST``/``ORACLE_SERVICE_NAME``. Production can
use an Autonomous Database wallet supplied as a base64-encoded zip through
``ORACLE_WALLET_BASE64`` so wallet files never need to be committed.
"""
from __future__ import annotations

import base64
import os
import tempfile
import threading
import zipfile
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path
from typing import Iterator

import oracledb
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session, sessionmaker

load_dotenv()


class OracleConnectionError(Exception):
    """Raised when an Oracle connection or pool cannot be created."""


_wallet_dir: Path | None = None
_wallet_lock = threading.Lock()


def _wallet_base64() -> str:
    chunks = [
        os.getenv(f"ORACLE_WALLET_BASE64_{index}", "").strip()
        for index in range(1, 9)
    ]
    chunked = "".join(chunk for chunk in chunks if chunk)
    return chunked or os.getenv("ORACLE_WALLET_BASE64", "").strip()


def _autonomous_enabled() -> bool:
    return bool(_wallet_base64())


def _prepare_wallet() -> Path:
    global _wallet_dir
    if _wallet_dir is not None:
        return _wallet_dir

    with _wallet_lock:
        if _wallet_dir is not None:
            return _wallet_dir

        encoded = _wallet_base64()
        if not encoded:
            raise OracleConnectionError("ORACLE_WALLET_BASE64 is not configured")

        try:
            archive_bytes = base64.b64decode(encoded, validate=True)
            target = Path(tempfile.gettempdir()) / "moodpick-oracle-wallet"
            target.mkdir(mode=0o700, parents=True, exist_ok=True)
            with zipfile.ZipFile(BytesIO(archive_bytes)) as archive:
                for member in archive.infolist():
                    member_path = Path(member.filename)
                    if member_path.is_absolute() or ".." in member_path.parts:
                        raise OracleConnectionError("Invalid path in Oracle wallet archive")
                archive.extractall(target)
        except (ValueError, zipfile.BadZipFile) as exc:
            raise OracleConnectionError("Invalid Oracle wallet data") from exc

        _wallet_dir = target
        return target


def _dsn() -> str:
    if _autonomous_enabled():
        return os.getenv("ORACLE_DSN", "moodpick_low")

    host = os.getenv("ORACLE_HOST", "")
    port = os.getenv("ORACLE_PORT", "1521")
    service_name = os.getenv("ORACLE_SERVICE_NAME", "")
    return oracledb.makedsn(host, port, service_name=service_name)


def _wallet_connect_args() -> dict[str, str]:
    if not _autonomous_enabled():
        return {}

    wallet_dir = str(_prepare_wallet())
    return {
        "config_dir": wallet_dir,
        "wallet_location": wallet_dir,
        "wallet_password": os.getenv("ORACLE_WALLET_PASSWORD", ""),
    }


def _sqlalchemy_url() -> URL:
    common = {
        "drivername": "oracle+oracledb",
        "username": os.getenv("ORACLE_USER", ""),
        "password": os.getenv("ORACLE_PASSWORD", ""),
    }
    if _autonomous_enabled():
        return URL.create(**common)

    return URL.create(
        **common,
        host=os.getenv("ORACLE_HOST", ""),
        port=int(os.getenv("ORACLE_PORT", "1521")),
        query={"service_name": os.getenv("ORACLE_SERVICE_NAME", "")},
    )


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
                **_wallet_connect_args(),
            )
        except oracledb.Error as exc:
            raise OracleConnectionError(f"Failed to create Oracle pool: {exc}") from exc
    return _pool


def _get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        connect_args = _wallet_connect_args()
        if _autonomous_enabled():
            connect_args["dsn"] = _dsn()
        _engine = create_engine(
            _sqlalchemy_url(),
            connect_args=connect_args,
            pool_pre_ping=True,
            pool_size=int(os.getenv("SQLALCHEMY_POOL_SIZE", "3")),
            max_overflow=int(os.getenv("SQLALCHEMY_MAX_OVERFLOW", "2")),
        )
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)
    return _engine


@contextmanager
def get_connection() -> Iterator[oracledb.Connection]:
    pool = _get_pool()
    try:
        conn = pool.acquire()
    except oracledb.Error as exc:
        raise OracleConnectionError(f"Failed to acquire Oracle connection: {exc}") from exc
    try:
        yield conn
    finally:
        pool.release(conn)


@contextmanager
def get_session() -> Iterator[Session]:
    _get_engine()
    assert _SessionLocal is not None
    session = _SessionLocal()
    try:
        yield session
    finally:
        session.close()


def check_connection() -> None:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM DUAL")
        cursor.fetchone()
