from typing import Literal

from pydantic import BaseModel, Field


class OnboardingRequest(BaseModel):
    visitor_token: str = Field(min_length=8, max_length=64)
    favorite_genres: list[str] = Field(min_length=1, max_length=5)
    moods: list[str] = Field(default_factory=list, max_length=3)
    favorite_movie: str | None = Field(default=None, max_length=200)


class ProfileResponse(BaseModel):
    visitor_token: str
    onboarding_completed: bool
    favorite_genres: list[str] = Field(default_factory=list)
    moods: list[str] = Field(default_factory=list)


class MovieRecommendation(BaseModel):
    id: int
    title: str
    overview: str = ""
    poster_url: str | None = None
    release_year: int | None = None
    rating: float = 0
    genres: list[str] = Field(default_factory=list)
    score: float
    reason: str


class MovieDetailResponse(BaseModel):
    id: int
    title: str
    overview: str = ""
    poster_url: str | None = None
    backdrop_url: str | None = None
    release_year: int | None = None
    release_date: str | None = None
    runtime: int | None = None
    rating: float = 0
    genres: list[str] = Field(default_factory=list)
    tagline: str | None = None
    trailer_url: str | None = None


class RecommendationResponse(BaseModel):
    recommendations: list[MovieRecommendation]


class FeedbackRequest(BaseModel):
    visitor_token: str = Field(min_length=8, max_length=64)
    movie_id: int
    movie_title: str = Field(max_length=200)
    genres: list[str] = Field(default_factory=list, max_length=10)
    action: Literal["liked", "disliked", "skipped", "watched"]


class FeedbackResponse(BaseModel):
    saved: bool
    message: str
