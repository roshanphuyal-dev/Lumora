"""Seed a fixed test account for local manual testing.

Run with: `uv run python scripts/seed_test_user.py` (from `backend/`).

Idempotent: if the account already exists, this reports it instead of erroring --
`auth_service.register_user` is reused as-is (same hashing/persistence path the real
`/auth/register` endpoint uses), not reimplemented here.
"""

import asyncio

from fastapi import HTTPException

from app.db.session import async_session_maker
from app.services import auth_service

TEST_EMAIL = "test@lumora.dev"
TEST_PASSWORD = "testpass123"
TEST_FULL_NAME = "Test Student"


async def main() -> None:
    async with async_session_maker() as db:
        try:
            await auth_service.register_user(db, TEST_EMAIL, TEST_PASSWORD, TEST_FULL_NAME)
            print(f"Created test user: {TEST_EMAIL}")
        except HTTPException as exc:
            if exc.status_code == 400:
                print(f"Test user already exists: {TEST_EMAIL}")
            else:
                raise

    print(
        f"\nLog in at http://localhost:5173/login with:\n"
        f"  email:    {TEST_EMAIL}\n"
        f"  password: {TEST_PASSWORD}"
    )


if __name__ == "__main__":
    asyncio.run(main())
