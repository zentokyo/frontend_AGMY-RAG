import os
from datetime import datetime, timezone

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Cookie, Depends, Response, status
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
    hash_password,
    hash_token,
    normalize_email,
    parse_duration,
    sign_jwt,
    verify_jwt,
)
from src.api.commons.internal_auth import require_internal_token
from src.api.commons.public_auth import require_app_auth

COOKIE_NAME = "appRefreshToken"

app_auth_router = APIRouter(
    prefix="/internal/app/auth",
    tags=["Internal App Auth"],
    dependencies=[Depends(require_internal_token)],
)
public_app_auth_router = APIRouter(
    prefix="/api/app/auth",
    tags=["App Auth"],
)


class RegisterAppUserRequest(BaseModel):
    email: str | None = None
    password: str | None = None
    username: str | None = None


class LoginAppUserRequest(BaseModel):
    email: str | None = None
    password: str | None = None


class RefreshAppTokenRequest(BaseModel):
    refresh_token: str | None = None


class LogoutAppUserRequest(BaseModel):
    refresh_token: str | None = None


@app_auth_router.post("/register", status_code=status.HTTP_201_CREATED)
@inject
async def register_app_user_handler(
    schema: RegisterAppUserRequest,
    session: FromDishka[AsyncSession],
):
    result = await _register_app_user(schema, session)
    if isinstance(result, JSONResponse):
        return result
    return JSONResponse(status_code=201, content=result)


@public_app_auth_router.post("/register", status_code=status.HTTP_201_CREATED)
@inject
async def register_public_app_user_handler(
    schema: RegisterAppUserRequest,
    response: Response,
    session: FromDishka[AsyncSession],
):
    result = await _register_app_user(schema, session)
    if isinstance(result, JSONResponse):
        return result

    _set_refresh_cookie(response, result["refreshToken"])
    return _auth_body(result)


async def _register_app_user(schema: RegisterAppUserRequest, session: AsyncSession):
    email = normalize_email(schema.email)
    password = schema.password or ""
    username = schema.username.strip() if schema.username and schema.username.strip() else None

    if not email or not password:
        return JSONResponse(status_code=400, content={"error": "Email and password are required"})
    if len(password) < 6:
        return JSONResponse(status_code=400, content={"error": "Password must be at least 6 characters"})

    async with session.begin():
        existing_result = await session.execute(
            text("SELECT id FROM app_users WHERE email = :email"),
            {"email": email},
        )
        if existing_result.mappings().first():
            return JSONResponse(status_code=409, content={"error": "User already exists"})

        password_hash = hash_password(password)
        user_result = await session.execute(
            text(
                """
                INSERT INTO app_users (email, password_hash, username)
                VALUES (:email, :password_hash, :username)
                RETURNING id, email, username
                """
            ),
            {"email": email, "password_hash": password_hash, "username": username},
        )
        user = user_result.mappings().first()

        tokens = await _issue_tokens(session, user)

    return _auth_response(user, tokens)


@app_auth_router.post("/login")
@inject
async def login_app_user_handler(
    schema: LoginAppUserRequest,
    session: FromDishka[AsyncSession],
):
    return await _login_app_user(schema, session)


@public_app_auth_router.post("/login")
@inject
async def login_public_app_user_handler(
    schema: LoginAppUserRequest,
    response: Response,
    session: FromDishka[AsyncSession],
):
    result = await _login_app_user(schema, session)
    if isinstance(result, JSONResponse):
        return result

    _set_refresh_cookie(response, result["refreshToken"])
    return _auth_body(result)


async def _login_app_user(schema: LoginAppUserRequest, session: AsyncSession):
    email = normalize_email(schema.email)
    password = schema.password or ""
    if not email or not password:
        return JSONResponse(status_code=400, content={"error": "Email and password are required"})

    async with session.begin():
        user_result = await session.execute(
            text("SELECT id, email, username, password_hash FROM app_users WHERE email = :email"),
            {"email": email},
        )
        user = user_result.mappings().first()
        if not user or not check_password(password, user["password_hash"]):
            return JSONResponse(status_code=401, content={"error": "Invalid credentials"})

        tokens = await _issue_tokens(session, user)

    return _auth_response(user, tokens)


@app_auth_router.post("/refresh")
@inject
async def refresh_app_token_handler(
    schema: RefreshAppTokenRequest,
    session: FromDishka[AsyncSession],
):
    return await _refresh_app_token(schema.refresh_token, session)


@public_app_auth_router.post("/refresh")
@inject
async def refresh_public_app_token_handler(
    response: Response,
    session: FromDishka[AsyncSession],
    refresh_token: str | None = Cookie(default=None, alias=COOKIE_NAME),
):
    result = await _refresh_app_token(refresh_token, session)
    if isinstance(result, JSONResponse):
        return result

    _set_refresh_cookie(response, result["refreshToken"])
    return {"accessToken": result["accessToken"]}


async def _refresh_app_token(refresh_token: str | None, session: AsyncSession):
    if not refresh_token:
        return JSONResponse(status_code=401, content={"error": "No refresh token"})

    payload = verify_jwt(refresh_token, JWT_REFRESH_SECRET)
    if payload is None:
        return JSONResponse(status_code=401, content={"error": "Invalid or expired refresh token"})
    if payload.get("type") != "app":
        return JSONResponse(status_code=403, content={"error": "Invalid token type"})

    token_hash = hash_token(refresh_token)
    async with session.begin():
        token_result = await session.execute(
            text(
                """
                SELECT id
                FROM app_refresh_tokens
                WHERE token_hash = :token_hash AND expires_at > NOW()
                """
            ),
            {"token_hash": token_hash},
        )
        if not token_result.mappings().first():
            return JSONResponse(status_code=401, content={"error": "Refresh token revoked"})

        await session.execute(
            text("DELETE FROM app_refresh_tokens WHERE token_hash = :token_hash"),
            {"token_hash": token_hash},
        )

        user = {
            "id": payload["sub"],
            "email": payload["email"],
            "username": payload.get("username"),
        }
        tokens = await _issue_tokens(session, user)

    return tokens


@app_auth_router.post("/logout")
@inject
async def logout_app_user_handler(
    schema: LogoutAppUserRequest,
    session: FromDishka[AsyncSession],
):
    return await _logout_app_user(schema.refresh_token, session)


@public_app_auth_router.post("/logout")
@inject
async def logout_public_app_user_handler(
    response: Response,
    session: FromDishka[AsyncSession],
    refresh_token: str | None = Cookie(default=None, alias=COOKIE_NAME),
):
    result = await _logout_app_user(refresh_token, session)
    response.delete_cookie(COOKIE_NAME, httponly=True, secure=_cookie_secure(), samesite="strict")
    return result


@public_app_auth_router.get("/me")
async def get_public_app_user_handler(user: dict = Depends(require_app_auth)):
    return {
        "user": {
            "id": user["sub"],
            "email": user["email"],
            "username": user.get("username"),
        }
    }


async def _logout_app_user(refresh_token: str | None, session: AsyncSession):
    if refresh_token:
        async with session.begin():
            await session.execute(
                text("DELETE FROM app_refresh_tokens WHERE token_hash = :token_hash"),
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
        "username": user["username"],
    }


async def _issue_tokens(session: AsyncSession, user) -> dict:
    payload = {
        "sub": user["id"],
        "email": user["email"],
        "username": user["username"],
        "type": "app",
    }
    access_token = sign_jwt(payload, JWT_SECRET, ACCESS_EXPIRES)
    refresh_token = sign_jwt(payload, JWT_REFRESH_SECRET, REFRESH_EXPIRES)
    await session.execute(
        text(
            """
            INSERT INTO app_refresh_tokens (user_id, token_hash, expires_at)
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
