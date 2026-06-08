import os
from datetime import datetime, timezone

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Cookie, Depends, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.commons.auth_tokens import (
    ACCESS_EXPIRES,
    JWT_REFRESH_SECRET,
    JWT_SECRET,
    REFRESH_EXPIRES,
    check_password,
    hash_token,
    normalize_email,
    parse_duration,
    sign_jwt,
    verify_jwt,
)
from src.api.commons.public_auth import require_admin_auth
from src.api.commons.internal_auth import require_internal_token

COOKIE_NAME = "refreshToken"

admin_auth_router = APIRouter(
    prefix="/internal/admin/auth",
    tags=["Internal Admin Auth"],
    dependencies=[Depends(require_internal_token)],
)
public_admin_auth_router = APIRouter(
    prefix="/api/auth",
    tags=["Admin Auth"],
)


class AdminLoginRequest(BaseModel):
    email: str | None = None
    password: str | None = None


class AdminRefreshRequest(BaseModel):
    refresh_token: str | None = None


class AdminLogoutRequest(BaseModel):
    refresh_token: str | None = None


@admin_auth_router.post("/login")
@inject
async def login_admin_handler(
    schema: AdminLoginRequest,
    session: FromDishka[AsyncSession],
):
    return await _login_admin(schema, session)


@public_admin_auth_router.post("/login")
@inject
async def login_public_admin_handler(
    schema: AdminLoginRequest,
    response: Response,
    session: FromDishka[AsyncSession],
):
    result = await _login_admin(schema, session)
    if isinstance(result, JSONResponse):
        return result

    _set_refresh_cookie(response, result["refreshToken"])
    return _auth_body(result)


async def _login_admin(schema: AdminLoginRequest, session: AsyncSession):
    email = normalize_email(schema.email)
    password = schema.password or ""
    if not email or not password:
        return JSONResponse(status_code=400, content={"error": "Email and password are required"})

    async with session.begin():
        user_result = await session.execute(
            text("SELECT id, email, role, password_hash FROM admin_users WHERE email = :email"),
            {"email": email},
        )
        user = user_result.mappings().first()
        if not user or not check_password(password, user["password_hash"]):
            return JSONResponse(status_code=401, content={"error": "Invalid credentials"})

        tokens = await _issue_tokens(session, user)

    return _auth_response(user, tokens)


@admin_auth_router.post("/refresh")
@inject
async def refresh_admin_token_handler(
    schema: AdminRefreshRequest,
    session: FromDishka[AsyncSession],
):
    return await _refresh_admin_token(schema.refresh_token, session)


@public_admin_auth_router.post("/refresh")
@inject
async def refresh_public_admin_token_handler(
    response: Response,
    session: FromDishka[AsyncSession],
    refresh_token: str | None = Cookie(default=None, alias=COOKIE_NAME),
):
    result = await _refresh_admin_token(refresh_token, session)
    if isinstance(result, JSONResponse):
        return result

    _set_refresh_cookie(response, result["refreshToken"])
    return {"accessToken": result["accessToken"]}


async def _refresh_admin_token(refresh_token: str | None, session: AsyncSession):
    if not refresh_token:
        return JSONResponse(status_code=401, content={"error": "No refresh token"})

    payload = verify_jwt(refresh_token, JWT_REFRESH_SECRET)
    if payload is None:
        return JSONResponse(status_code=401, content={"error": "Invalid or expired refresh token"})

    token_hash = hash_token(refresh_token)
    async with session.begin():
        token_result = await session.execute(
            text(
                """
                SELECT id
                FROM admin_refresh_tokens
                WHERE token_hash = :token_hash AND expires_at > NOW()
                """
            ),
            {"token_hash": token_hash},
        )
        if not token_result.mappings().first():
            return JSONResponse(status_code=401, content={"error": "Refresh token revoked"})

        await session.execute(
            text("DELETE FROM admin_refresh_tokens WHERE token_hash = :token_hash"),
            {"token_hash": token_hash},
        )

        user = {
            "id": payload["sub"],
            "email": payload["email"],
            "role": payload.get("role"),
        }
        tokens = await _issue_tokens(session, user)

    return tokens


@admin_auth_router.post("/logout")
@inject
async def logout_admin_handler(
    schema: AdminLogoutRequest,
    session: FromDishka[AsyncSession],
):
    return await _logout_admin(schema.refresh_token, session)


@public_admin_auth_router.post("/logout")
@inject
async def logout_public_admin_handler(
    response: Response,
    session: FromDishka[AsyncSession],
    refresh_token: str | None = Cookie(default=None, alias=COOKIE_NAME),
):
    result = await _logout_admin(refresh_token, session)
    response.delete_cookie(COOKIE_NAME, httponly=True, secure=_cookie_secure(), samesite="strict")
    return result


@public_admin_auth_router.get("/me")
async def get_public_admin_me_handler(user: dict = Depends(require_admin_auth)):
    return {
        "id": user["sub"],
        "email": user["email"],
        "role": user.get("role"),
    }


async def _logout_admin(refresh_token: str | None, session: AsyncSession):
    if refresh_token:
        async with session.begin():
            await session.execute(
                text("DELETE FROM admin_refresh_tokens WHERE token_hash = :token_hash"),
                {"token_hash": hash_token(refresh_token)},
            )

    return {"message": "Logged out"}


def _auth_body(body: dict) -> dict:
    return {
        "accessToken": body["accessToken"],
        "user": body["user"],
    }


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=_cookie_secure(),
        samesite="strict",
        max_age=int(parse_duration(REFRESH_EXPIRES).total_seconds()),
    )


def _cookie_secure() -> bool:
    return os.getenv("COOKIE_SECURE", "false").lower() in ("true", "1", "yes")


def _auth_response(user, tokens: dict) -> dict:
    return {
        "accessToken": tokens["accessToken"],
        "refreshToken": tokens["refreshToken"],
        "user": _user_response(user),
    }


def _user_response(user) -> dict:
    return {
        "id": user["id"],
        "email": user["email"],
        "role": user["role"],
    }


async def _issue_tokens(session: AsyncSession, user) -> dict:
    payload = {
        "sub": user["id"],
        "email": user["email"],
        "role": user["role"],
    }
    access_token = sign_jwt(payload, JWT_SECRET, ACCESS_EXPIRES)
    refresh_token = sign_jwt(payload, JWT_REFRESH_SECRET, REFRESH_EXPIRES)
    await session.execute(
        text(
            """
            INSERT INTO admin_refresh_tokens (user_id, token_hash, expires_at)
            VALUES (:user_id, :token_hash, :expires_at)
            """
        ),
        {
            "user_id": user["id"],
            "token_hash": hash_token(refresh_token),
            "expires_at": datetime.now(timezone.utc) + parse_duration(REFRESH_EXPIRES),
        },
    )
    return {"accessToken": access_token, "refreshToken": refresh_token}
