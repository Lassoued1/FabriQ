from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

_ALGORITHM = "HS256"


@dataclass
class UserContext:
    user_id: str
    email: str
    tenant_id: str
    role: str  # "admin" | "viewer"


@dataclass
class _UserRecord:
    user_id: str
    email: str
    hashed_password: str
    tenant_id: str
    role: str


def _jwt_secret() -> str:
    secret = os.environ.get("FABRIQ_JWT_SECRET", "")
    if not secret:
        raise RuntimeError("FABRIQ_JWT_SECRET must be set in environment.")
    return secret


def _jwt_expire_minutes() -> int:
    try:
        return int(os.environ.get("FABRIQ_JWT_EXPIRE_MINUTES", "60"))
    except ValueError:
        return 60


def load_users_from_env() -> dict[str, _UserRecord]:
    """Parse FABRIQ_USERS=email:hashed_pw:tenant_id:role,... into a lookup dict."""
    raw = os.environ.get("FABRIQ_USERS", "")
    users: dict[str, _UserRecord] = {}
    if not raw:
        return users
    for entry in raw.split(","):
        parts = entry.strip().split(":")
        if len(parts) < 4:
            continue
        email, hashed_pw, tenant_id, role = parts[0], parts[1], parts[2], parts[3]
        users[email] = _UserRecord(
            user_id=email,
            email=email,
            hashed_password=hashed_pw,
            tenant_id=tenant_id,
            role=role,
        )
    return users


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        # Hash malforme (ex. placeholder) -> refus, pas d'erreur 500
        return False


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=_jwt_expire_minutes()))
    payload = {**data, "exp": expire}
    return jwt.encode(payload, _jwt_secret(), algorithm=_ALGORITHM)


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, _jwt_secret(), algorithms=[_ALGORITHM])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def authenticate_user(email: str, password: str) -> UserContext | None:
    from .disabled_users import is_disabled
    users = load_users_from_env()
    record = users.get(email)
    if record is None or not verify_password(password, record.hashed_password):
        return None
    if is_disabled(email):
        return None
    return UserContext(
        user_id=record.user_id,
        email=record.email,
        tenant_id=record.tenant_id,
        role=record.role,
    )


def list_users() -> list[UserContext]:
    """Return all users without passwords — for admin display only."""
    return [
        UserContext(user_id=r.user_id, email=r.email, tenant_id=r.tenant_id, role=r.role)
        for r in load_users_from_env().values()
    ]


def get_current_user(token: str = Depends(_oauth2_scheme)) -> UserContext:
    from .disabled_users import is_disabled
    payload = decode_access_token(token)
    email: str | None = payload.get("sub")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide : champ sub manquant.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    users = load_users_from_env()
    record = users.get(email)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur introuvable.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if is_disabled(email):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Compte désactivé.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return UserContext(
        user_id=record.user_id,
        email=record.email,
        tenant_id=record.tenant_id,
        role=record.role,
    )


def require_admin(user: UserContext = Depends(get_current_user)) -> UserContext:
    """Dependency that raises 403 unless the authenticated user has role='admin'."""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux administrateurs.",
        )
    return user
