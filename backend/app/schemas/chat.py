from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class Intent(str, Enum):
    """발화 분류 결과. routers/classify.py가 반환하는 값과 1:1로 맞춘다."""

    RECOMMEND = "recommend"
    NL2SQL = "nl2sql"
    VISUALIZE = "visualize"
    CHITCHAT = "chitchat"


class BookPreferences(BaseModel):
    genre: str = Field(min_length=1, max_length=30)
    topic: str = Field(min_length=1, max_length=50)
    reading_mood: str = Field(min_length=1, max_length=50)
    age_group: Literal["초등학생", "중학생", "고등학생", "20대", "30대", "40대", "50대 이상"]
    gender: Literal["여성", "남성", "논바이너리", "응답하지 않음"]
    mbti: str = Field(pattern=r"^[EI][NS][TF][JP]$")


class ChatRequest(BaseModel):
    session_id: str
    message: str
    recommendation_context: dict[str, Any] | None = None
    exclude_movie_ids: list[int] = Field(default_factory=list, max_length=500)
    book_preferences: BookPreferences | None = None


class ChatResponse(BaseModel):
    intent: Intent
    reply: str
    data: dict[str, Any] | None = None
