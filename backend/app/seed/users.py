"""Deterministic demo and developer account seeding."""

import json
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from pydantic import BaseModel, EmailStr, Field, TypeAdapter
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import hash_password, verify_password
from app.db.repo.users import get_user_by_email, upsert_user


class SeedUser(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


def validate_users(path: Path) -> list[SeedUser]:
    records = TypeAdapter(list[SeedUser]).validate_python(
        json.loads(path.read_text(encoding="utf-8"))
    )
    emails = [str(record.email).lower() for record in records]
    if len(emails) != len(set(emails)):
        raise ValueError("duplicate user email")
    return records


async def seed_users(session: AsyncSession, path: Path) -> int:
    records = validate_users(path)
    for record in records:
        email = str(record.email).lower()
        user_id = uuid5(NAMESPACE_URL, email)
        existing = await get_user_by_email(session, email)
        if existing is not None and existing.id == user_id:
            try:
                if verify_password(record.password, existing.password_hash):
                    continue
            except ValueError:
                pass
        await upsert_user(session, user_id, email, hash_password(record.password))
    return len(records)
