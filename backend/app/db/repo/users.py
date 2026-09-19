"""User persistence; transaction ownership remains with the caller."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

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
    name: str | None = None


def _to_row(user: User) -> UserRow:
    return UserRow(user.id, user.email, user.password_hash, user.created_at, user.name)


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


async def create_user(
    session: AsyncSession, email: str, password_hash: str, name: str | None
) -> UUID | None:
    """Insert a new user; None when the email is already taken."""
    statement = (
        insert(User)
        .values(id=uuid4(), email=email, password_hash=password_hash, name=name)
        .on_conflict_do_nothing(index_elements=[User.email])
        .returning(User.id)
    )
    return await session.scalar(statement)
