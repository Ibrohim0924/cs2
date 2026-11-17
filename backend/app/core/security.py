import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qsl

from fastapi import HTTPException, status
from jose import JWTError, jwt
from pwdlib import PasswordHash

from app.core.config import settings

ALGORITHM = "HS256"
password_hash = PasswordHash.recommended()


def validate_telegram_init_data(init_data: str) -> dict:
    if not settings.telegram_bot_token:
        raise HTTPException(status_code=503, detail="Telegram authentication is not configured")
    try:
        pairs = dict(parse_qsl(init_data, strict_parsing=True))
        received_hash = pairs.pop("hash")
        auth_date = int(pairs["auth_date"])
        user = json.loads(pairs["user"])
    except (ValueError, KeyError, json.JSONDecodeError):
        raise HTTPException(status_code=401, detail="Invalid Telegram initData") from None

    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(pairs.items()))
    secret_key = hmac.new(b"WebAppData", settings.telegram_bot_token.encode(), hashlib.sha256).digest()
    expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_hash, received_hash):
        raise HTTPException(status_code=401, detail="Invalid Telegram initData signature")
    now = int(time.time())
    if auth_date > now + 30 or now - auth_date > 86400:
        raise HTTPException(status_code=401, detail="Telegram initData has expired")
    if not isinstance(user.get("id"), int):
        raise HTTPException(status_code=401, detail="Invalid Telegram user")
    return user


def create_access_token(subject: str, role: str = "user") -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.admin_token_ttl_minutes)
    return jwt.encode({"sub": subject, "role": role, "exp": expires}, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session") from None


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)
