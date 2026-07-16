import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, chat, health, personalization

load_dotenv()

# httpx의 INFO 로그에는 API 키가 포함된 전체 요청 URL이 기록될 수 있다.
logging.getLogger("httpx").setLevel(logging.WARNING)

app = FastAPI(title="MoodPick API")

_frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[_frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(personalization.router)
