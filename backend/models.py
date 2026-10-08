from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("full_name")
    @classmethod
    def trim_name(cls, value: str) -> str:
        return value.strip()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserPublic(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    created_at: datetime


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


class SessionCreate(BaseModel):
    role: str = Field(min_length=2, max_length=120)
    interview_type: Literal["Behavioral", "Technical", "Mixed"]
    difficulty: Literal["Beginner", "Intermediate", "Advanced"]


class InterviewQuestion(BaseModel):
    category: str
    prompt: str
    hint: str


class InterviewSessionPublic(BaseModel):
    id: str
    role: str
    interview_type: str
    difficulty: str
    status: Literal["in_progress", "completed"]
    questions: list[InterviewQuestion]
    answers: list[dict]
    created_at: datetime
    completed_at: datetime | None = None
    report: dict | None = None
    model_config = ConfigDict(extra="ignore")


class AnswerRequest(BaseModel):
    question_index: int = Field(ge=0, le=19)
    answer: str = Field(min_length=1, max_length=12000)


class HealthResponse(BaseModel):
    status: str
    database: str
    ai: str
