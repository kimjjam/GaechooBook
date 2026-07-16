from enum import Enum
from typing import Any

from pydantic import BaseModel


class Intent(str, Enum):
    """발화 분류 결과. routers/classify.py가 반환하는 값과 1:1로 맞춘다."""

    RECOMMEND = "recommend"
    NL2SQL = "nl2sql"
    VISUALIZE = "visualize"
    CHITCHAT = "chitchat"


class ChatRequest(BaseModel):
    session_id: str
    message: str
    recommendation_context: dict[str, Any] | None = None


class ChatResponse(BaseModel):
    intent: Intent
    reply: str
    data: dict[str, Any] | None = None
