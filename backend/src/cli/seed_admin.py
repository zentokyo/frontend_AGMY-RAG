import argparse
import asyncio
import os

import asyncpg

from src.api.commons.auth_tokens import hash_password, normalize_email
from src.config import config


async def seed_admin(email: str, password: str) -> None:
    normalized_email = normalize_email(email)
    if not normalized_email or not password:
        raise ValueError("Admin email and password are required")
    if len(password) < 8:
        raise ValueError("Admin password must be at least 8 characters")

    connection = await asyncpg.connect(
        host=config.postgres.host,
        port=config.postgres.port,
        user=config.postgres.user,
        password=config.postgres.password,
        database=config.postgres.db,
    )
    try:
        admin_id = await connection.fetchval(
            """
            INSERT INTO admin_users (email, password_hash, role)
            VALUES ($1, $2, 'admin')
            ON CONFLICT (email)
            DO UPDATE SET password_hash = EXCLUDED.password_hash, role = 'admin'
            RETURNING id
            """,
            normalized_email,
            hash_password(password),
        )
    finally:
        await connection.close()

    print(f"Admin user seeded: {normalized_email} (id={admin_id})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or update the first admin user")
    parser.add_argument(
        "--email",
        default=os.getenv("SEED_ADMIN_EMAIL", "admin@example.com"),
    )
    parser.add_argument(
        "--password",
        default=os.getenv("SEED_ADMIN_PASSWORD", "Admin123!"),
    )
    args = parser.parse_args()
    asyncio.run(seed_admin(args.email, args.password))


if __name__ == "__main__":
    main()
