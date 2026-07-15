from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    visitor_token: str = Field(min_length=8, max_length=64)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    nickname: str = Field(min_length=1, max_length=30)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class AuthUser(BaseModel):
    id: int
    email: str
    nickname: str


class AuthResponse(BaseModel):
    user: AuthUser
    csrf_token: str


class LogoutResponse(BaseModel):
    logged_out: bool
