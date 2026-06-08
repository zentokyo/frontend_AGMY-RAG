from fastapi import Header, HTTPException, Request, status

from src.api.commons.auth_tokens import JWT_SECRET, verify_jwt


async def require_admin_auth(authorization: str | None = Header(default=None)) -> dict:
    payload = _verify_access_token(authorization)
    if payload.get("type") == "app" or payload.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid token type",
        )

    return payload


async def require_app_auth(
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict:
    payload = _verify_access_token(authorization)
    if payload.get("type") != "app":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid token type",
        )

    try:
        int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
        )

    request.state.app_user = payload
    return payload


def get_app_user_id(request: Request) -> int:
    payload = getattr(request.state, "app_user", None)
    if payload is not None:
        return int(payload["sub"])

    path_user_id = request.path_params.get("user_id")
    if path_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing app user",
        )

    try:
        return int(path_user_id)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user id",
        )


def _verify_access_token(authorization: str | None) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token",
        )

    payload = verify_jwt(authorization[7:], JWT_SECRET)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    return payload
