"""User persistence; transaction ownership remains with the caller."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User


@dataclass(frozen=True)
class UserRow:
    id: UUID
    email: str
    password_hash: str
    created_at: datetime


def _to_row(user: User) -> UserRow:
    return UserRow(user.id, user.email, user.password_hash, user.created_at)


async def get_user_by_email(session: AsyncSession, email: str) -> UserRow | None:
    user = await session.scalar(select(User).where(User.email == email))
    return _to_row(user) if user is not None else None


async def get_user(session: AsyncSession, user_id: UUID) -> UserRow | None:
    user = await session.get(User, user_id)
    return _to_row(user) if user is not None else None


async def upsert_user(
    session: AsyncSession, id: UUID, email: str, password_hash: str
) -> None:
    statement = insert(User).values(id=id, email=email, password_hash=password_hash)
    await session.execute(
        statement.on_conflict_do_update(
            index_elements=[User.id],
            set_={"email": email, "password_hash": password_hash},
        )
    )
