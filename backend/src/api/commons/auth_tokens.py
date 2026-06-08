import base64
import hashlib
import hmac
import json
import os
import re
from datetime import datetime, timedelta, timezone

import bcrypt

ACCESS_EXPIRES = os.getenv("ACCESS_TOKEN_EXPIRES", "15m")
REFRESH_EXPIRES = os.getenv("REFRESH_TOKEN_EXPIRES", "7d")
JWT_SECRET = os.getenv("JWT_SECRET", "change_me_access_use_long_random_string")
JWT_REFRESH_SECRET = os.getenv("JWT_REFRESH_SECRET", "change_me_refresh_different_long_random_string")


def normalize_email(email: str | None) -> str:
    return email.strip().lower() if email else ""


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def check_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def sign_jwt(payload: dict, secret: str, expires_in: str) -> str:
    now = int(datetime.now(timezone.utc).timestamp())
    body = {**payload, "iat": now, "exp": now + int(parse_duration(expires_in).total_seconds())}
    header = {"alg": "HS256", "typ": "JWT"}
    signing_input = ".".join([_b64_json(header), _b64_json(body)])
    signature = hmac.new(secret.encode("utf-8"), signing_input.encode("utf-8"), hashlib.sha256).digest()
    return f"{signing_input}.{_b64url(signature)}"


def verify_jwt(token: str, secret: str) -> dict | None:
    try:
        header_part, payload_part, signature_part = token.split(".")
        signing_input = f"{header_part}.{payload_part}"
        expected = _b64url(
            hmac.new(secret.encode("utf-8"), signing_input.encode("utf-8"), hashlib.sha256).digest()
        )
        if not hmac.compare_digest(expected, signature_part):
            return None

        payload = json.loads(_b64url_decode(payload_part))
        if int(payload.get("exp", 0)) <= int(datetime.now(timezone.utc).timestamp()):
            return None
        return payload
    except Exception:
        return None


def parse_duration(value: str) -> timedelta:
    match = re.fullmatch(r"\s*(\d+)\s*([smhd])\s*", value or "")
    if not match:
        return timedelta(minutes=15)

    amount = int(match.group(1))
    unit = match.group(2)
    if unit == "s":
        return timedelta(seconds=amount)
    if unit == "m":
        return timedelta(minutes=amount)
    if unit == "h":
        return timedelta(hours=amount)
    return timedelta(days=amount)


def _b64_json(value: dict) -> str:
    data = json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return _b64url(data)


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> str:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}").decode("utf-8")
