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


ROLE_RANK: dict[Role, int] = {
    Role.viewer: 0,
    Role.operator: 1,
    Role.supervisor: 2,
    Role.admin: 3,
    Role.auditor: 2,  # auditor rank similar to supervisor for read audit
    Role.system: 99,
}

# Action -> minimal roles allowed. Enterprise gov-grade mapping.
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
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization header missing")
    return _decode_token(credentials.credentials)


def require_role(*allowed: Role):
    allowed_set = set(allowed)

    async def _check(actor: Actor = Depends(current_actor)) -> Actor:
        if actor.role not in allowed_set and actor.role != Role.system:
            # also check rank: system bypass, admin bypass if allowed contains anything < admin?
            # Strict: must be explicit unless system.
            # But allow higher rank to pass for convenience: e.g., admin can do operator.
            # We'll implement rank-based if actor rank >= max required rank OR role explicitly allowed.
            # Simpler: if rank check passes and actor role rank >= min allowed rank?
            # For gov-grade, we keep explicit but also allow rank escalation.
            actor_rank = ROLE_RANK.get(actor.role, 0)
            min_required_rank = min((ROLE_RANK.get(r, 0) for r in allowed_set), default=0)
            if actor_rank < min_required_rank and actor.role != Role.system:
                # final check: is actor role in ACTION_ROLES supermap? No.
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Role {actor.role} not permitted. Requires {', '.join(r.value for r in allowed_set)}")
        return actor

    return _check


def require_action(action: str):
    roles = ACTION_ROLES.get(action, {Role.admin, Role.system})

    async def _check(actor: Actor = Depends(current_actor)) -> Actor:
        if actor.role not in roles and actor.role != Role.system:
            # rank fallback: allow if rank >= minimal rank for this action
            actor_rank = ROLE_RANK.get(actor.role, 0)
            min_rank = min(ROLE_RANK.get(r, 0) for r in roles)
            if actor_rank < min_rank:
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
