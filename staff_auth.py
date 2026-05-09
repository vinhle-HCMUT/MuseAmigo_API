import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

import models
from database import get_db

SECRET = os.environ.get("STAFF_JWT_SECRET", "dev-staff-secret-change-in-production")
_bearer = HTTPBearer(auto_error=False)


def effective_role(user: models.User) -> str:
    """Canonical role: superadmin | manager | visitor (maps legacy user / museum_manager)."""
    r = (user.role or "").strip()
    if r in ("", "user"):
        return "visitor"
    if r == "museum_manager":
        return "manager"
    return r


def create_staff_token(user_id: int, role: str, managed_museum_id: int | None) -> str:
    payload: dict[str, Any] = {
        "sub": user_id,
        "role": role,
        "mid": managed_museum_id,
        "exp": int(time.time()) + 86400 * 7,
    }
    body = (
        base64.urlsafe_b64encode(
            json.dumps(payload, separators=(",", ":")).encode("utf-8")
        )
        .decode("ascii")
        .rstrip("=")
    )
    sig = hmac.new(SECRET.encode("utf-8"), body.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{body}.{sig}"


def _decode_payload(token: str) -> dict[str, Any]:
    try:
        body, sig = token.rsplit(".", 1)
        expected = hmac.new(SECRET.encode("utf-8"), body.encode("ascii"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, sig):
            raise ValueError("signature")
        pad = (4 - len(body) % 4) % 4
        padded = body + ("=" * pad)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
        if int(payload.get("exp", 0)) < time.time():
            raise ValueError("expired")
        return payload
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc


def get_current_staff(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> models.User:
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    payload = _decode_payload(credentials.credentials)
    user_id = int(payload["sub"])
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user or effective_role(user) not in ("superadmin", "manager"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff access required",
        )
    return user


def get_current_superadmin(
    user: models.User = Depends(get_current_staff),
) -> models.User:
    if effective_role(user) != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superadmin only",
        )
    return user


def ensure_museum_scope(user: models.User, museum_id: int) -> None:
    if effective_role(user) == "superadmin":
        return
    if effective_role(user) == "manager" and user.managed_museum_id == museum_id:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You can only manage your assigned museum",
    )
