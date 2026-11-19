#!/usr/bin/env python
"""Create one local demo user without storing credentials in source control."""

import asyncio
import os

import kunpeng.models  # noqa: F401 - register all SQLAlchemy models
from sqlalchemy import select

from kunpeng.config import settings
from kunpeng.core.database import AsyncSessionLocal, engine
from kunpeng.core.security import get_password_hash
from kunpeng.models.base import Base
from kunpeng.models.user import User


def required_environment() -> tuple[str, str]:
    if settings.environment == "production":
        raise SystemExit("Refusing to create a demo user in production.")

    email = os.getenv("DEMO_EMAIL", "").strip()
    password = os.getenv("DEMO_PASSWORD", "")
    if not email or not password:
        raise SystemExit("Set DEMO_EMAIL and DEMO_PASSWORD before running this script.")
    if len(password) < 12:
        raise SystemExit("DEMO_PASSWORD must contain at least 12 characters.")
    return email, password


async def main() -> None:
    email, password = required_environment()

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        existing = (
            await session.execute(select(User).where(User.email == email))
        ).scalar_one_or_none()
        if existing:
            print(f"Demo user already exists: {email}")
            return

        session.add(
            User(
                email=email,
                hashed_password=get_password_hash(password),
                full_name="Demo User",
                is_active=True,
                is_superuser=True,
            )
        )
        await session.commit()
        print(f"Created local demo user: {email}")


if __name__ == "__main__":
    asyncio.run(main())
