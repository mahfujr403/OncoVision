"""Seed fixed demo credentials for recruiter/reviewer sign-in.

Creates (or resets) exactly two accounts so anyone evaluating the project
can log in immediately without registering:

    admin@oncovision.ai / Demo@Admin123   (role: admin)
    user@oncovision.ai  / Demo@User123    (role: user)

Safe to run multiple times: if an account already exists it is updated
in place (password reset, activated, verified) rather than duplicated.

Usage (from the `backend/` directory, with the venv/deps installed and
DATABASE_URL pointing at the target database):

    python -m scripts.seed_demo_users

Do NOT run this against a real production database with real user data --
it is intended for demo/staging deployments only.
"""

import asyncio

from app.database.session import AsyncSessionLocal
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.password_service import PasswordService

DEMO_ACCOUNTS = [
    {
        "full_name": "Demo Admin",
        "email": "admin@oncovision.ai",
        "password": "Demo@Admin123",
        "role": UserRole.ADMIN,
    },
    {
        "full_name": "Demo User",
        "email": "user@oncovision.ai",
        "password": "Demo@User123",
        "role": UserRole.USER,
    },
]


async def seed_demo_users() -> None:
    password_service = PasswordService()

    async with AsyncSessionLocal() as session:
        users = UserRepository(session)

        for account in DEMO_ACCOUNTS:
            password_hash = password_service.hash_password(account["password"])
            existing = await users.get_by_email(account["email"])

            if existing is not None:
                existing.full_name = account["full_name"]
                existing.password_hash = password_hash
                existing.role = account["role"]
                existing.is_active = True
                existing.is_verified = True
                await session.flush()
                print(f"Updated existing demo account: {account['email']} ({account['role'].value})")
                continue

            new_user = User(
                full_name=account["full_name"],
                email=account["email"],
                password_hash=password_hash,
                role=account["role"],
                is_active=True,
                is_verified=True,
            )
            await users.create(new_user)
            print(f"Created demo account: {account['email']} ({account['role'].value})")

        await session.commit()

    print("\nDemo credentials ready:")
    for account in DEMO_ACCOUNTS:
        print(f"  {account['role'].value:<6} -> {account['email']} / {account['password']}")


if __name__ == "__main__":
    asyncio.run(seed_demo_users())
