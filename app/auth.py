from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.config import settings

# ---- Roles ----

class Role(str, Enum):
    viewer = "viewer"
    operator = "operator"
    supervisor = "supervisor"
    admin = "admin"
    auditor = "auditor"
    system = "system"


# Action -> minimal roles allowed for the prototype policy.
ACTION_ROLES: dict[str, set[Role]] = {
    "view": {Role.viewer, Role.operator, Role.supervisor, Role.admin, Role.auditor, Role.system},
    "assess": {Role.operator, Role.supervisor, Role.admin, Role.system},
    "approve": {Role.supervisor, Role.admin, Role.system},
    "reject": {Role.operator, Role.supervisor, Role.admin, Role.system},
    "feedback": {Role.operator, Role.supervisor, Role.admin, Role.system},
    "retire_memory": {Role.supervisor, Role.admin, Role.system},
    "deliver_cap": {Role.supervisor, Role.admin, Role.system},
    "deliver_webeoc": {Role.supervisor, Role.admin, Role.system},
    "predict": {Role.operator, Role.supervisor, Role.admin, Role.system},
    "routing": {Role.operator, Role.supervisor, Role.admin, Role.system},
    "audit_read": {Role.auditor, Role.supervisor, Role.admin, Role.system},
    "audit_verify": {Role.auditor, Role.admin, Role.system},
    "after_action": {Role.supervisor, Role.admin, Role.auditor, Role.system},
    "admin": {Role.admin, Role.system},
}

bearer_scheme = HTTPBearer(auto_error=False)


class Actor(BaseModel):
    sub: str
    role: Role
    exp: datetime | None = None
    iat: datetime | None = None

    @property
    def is_system(self) -> bool:
        return self.role == Role.system


def _decode_token(token: str) -> Actor:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        role_raw = payload.get("role", "viewer")
        try:
            role = Role(role_raw)
        except ValueError:
            role = Role.viewer
        sub = str(payload.get("sub", "anonymous"))
        exp = None
        iat = None
        if "exp" in payload:
            exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        if "iat" in payload:
            iat = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)
        return Actor(sub=sub, role=role, exp=exp, iat=iat)
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {exc}") from exc


async def current_actor(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)) -> Actor:
    # When RBAC disabled (demo mode), return system role to avoid friction.
    if not settings.enable_rbac:
        return Actor(sub="demo-system", role=Role.system)
    if not settings.has_secure_auth:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Role-based access control is enabled but secure JWT and bootstrap secrets are not configured.",
        )
    # A public deployment may expose source evidence and already-created
    # decisions without exposing any mutating or model-backed operation.
    # ACTION_ROLES grants the viewer role only the explicit `view` action.
    if credentials is None or not credentials.credentials:
        return Actor(sub="anonymous", role=Role.viewer)
    return _decode_token(credentials.credentials)


def require_role(*allowed: Role):
    allowed_set = set(allowed)

    async def _check(actor: Actor = Depends(current_actor)) -> Actor:
        if actor.role not in allowed_set and actor.role != Role.system:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Role {actor.role} not permitted. Requires {', '.join(r.value for r in allowed_set)}")
        return actor

    return _check


def require_action(action: str):
    roles = ACTION_ROLES.get(action, {Role.admin, Role.system})

    async def _check(actor: Actor = Depends(current_actor)) -> Actor:
        if actor.role not in roles and actor.role != Role.system:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Action '{action}' requires one of {', '.join(r.value for r in roles)}; got {actor.role}",
            )
        return actor

    return _check


def create_token(sub: str, role: Role, expires_minutes: int = 60 * 8) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": sub,
        "role": role.value,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=expires_minutes)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
