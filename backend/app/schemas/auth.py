"""Authentication request and student identity schemas."""

from uuid import UUID

from pydantic import BaseModel, EmailStr


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class StudentCtx(BaseModel):
    student_id: UUID
    email: str
