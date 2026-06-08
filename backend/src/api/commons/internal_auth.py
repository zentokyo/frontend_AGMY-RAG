import os
import secrets

from fastapi import Header, HTTPException, status

INTERNAL_API_TOKEN = os.getenv("INTERNAL_API_TOKEN")


async def require_internal_token(x_internal_token: str | None = Header(default=None, alias="X-Internal-Token")):
    if not INTERNAL_API_TOKEN:
        return
    if not x_internal_token or not secrets.compare_digest(x_internal_token, INTERNAL_API_TOKEN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid internal API token",
        )
