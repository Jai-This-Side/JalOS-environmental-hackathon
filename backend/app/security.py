"""Scrypt password hashing and compact HS256 access tokens."""
import base64
import binascii
import hashlib
import hmac
import json
import os
import time
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from app.database import SessionLocal
from app.models import User
from app.passwords import hash_password, verify_password

JWT_SECRET = os.getenv("JWT_SECRET", "")
if len(JWT_SECRET.encode()) < 32:
    raise RuntimeError("Set JWT_SECRET to a random value of at least 32 bytes")
JWT_TTL_SECONDS = int(os.getenv("JWT_TTL_SECONDS", "3600"))
bearer_scheme = HTTPBearer(auto_error=False)

def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")

def create_access_token(user: User) -> str:
    now = int(time.time())
    header = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload = _b64(json.dumps({"sub": str(user.id), "role": user.role, "iat": now, "exp": now + JWT_TTL_SECONDS}, separators=(",", ":")).encode())
    unsigned = f"{header}.{payload}"
    signature = _b64(hmac.new(JWT_SECRET.encode(), unsigned.encode(), hashlib.sha256).digest())
    return f"{unsigned}.{signature}"

def user_from_token(token: str) -> User | None:
    try:
        if len(token) > 8192: return None
        header, payload, signature = token.split(".")
        jwt_header = json.loads(base64.urlsafe_b64decode(header + "=" * (-len(header) % 4)))
        if jwt_header.get("alg") != "HS256" or jwt_header.get("typ") != "JWT": return None
        unsigned = f"{header}.{payload}"
        expected = _b64(hmac.new(JWT_SECRET.encode(), unsigned.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected): return None
        claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        if int(claims["exp"]) <= int(time.time()): return None
        with SessionLocal() as session:
            user = session.get(User, int(claims["sub"]))
            if user is None or not user.is_active or user.role != claims.get("role"): return None
            session.expunge(user)
            return user
    except (ValueError, KeyError, TypeError, AttributeError, json.JSONDecodeError, binascii.Error):
        return None

def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)) -> User:
    user = user_from_token(credentials.credentials) if credentials is not None and credentials.scheme.lower() == "bearer" else None
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or expired access token", headers={"WWW-Authenticate": "Bearer"})
    return user

def require_admin(user: User = Depends(current_user)) -> User:
    if user.role not in {"ADMIN", "SUPER_ADMIN"}:
        raise HTTPException(status_code=403, detail="Administrator role required")
    return user
