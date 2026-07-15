from fastapi import APIRouter, HTTPException

from app.db.oracle_client import OracleConnectionError, check_connection

router = APIRouter()


@router.get("/health/db")
def health_db():
    try:
        check_connection()
    except OracleConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"status": "ok"}
