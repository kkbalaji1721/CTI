"""FastAPI dependencies: JWT auth -> tenant context, RBAC, rate limiting."""
from dataclasses import dataclass
from typing import Optional

import jwt
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from . import config
from .db import get_db
from .rate_limit import check_rate_limit
from .security import decode_token

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
    id: str
    tenant_id: str
    username: str
    role: str

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


def _unauthorized(msg: str = "Invalid or missing token") -> HTTPException:
    return HTTPException(status_code=401, detail=msg, headers={"WWW-Authenticate": "Bearer"})


def get_current_user(creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)) -> CurrentUser:
    """The tenant_id ALWAYS comes from the verified JWT - never from the client's query string."""
    if creds is None:
        raise _unauthorized()
    try:
        payload = decode_token(creds.credentials)
        user_oid = ObjectId(payload["sub"])
        tenant_id = payload["tenant_id"]
    except (jwt.PyJWTError, KeyError, InvalidId, TypeError):
        raise _unauthorized()

    # Re-check the user in the DB so deleted users / changed roles take effect immediately.
    user = get_db().users.find_one({"_id": user_oid, "tenant_id": tenant_id})
    if user is None:
        raise _unauthorized("User no longer exists")
    return CurrentUser(id=str(user["_id"]), tenant_id=user["tenant_id"], username=user["username"], role=user["role"])


def rate_limited_user(response: Response, user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """Authenticated + rate limited (per tenant/user)."""
    check_rate_limit(f"user:{user.tenant_id}:{user.id}", response)
    return user


def require_admin(user: CurrentUser = Depends(rate_limited_user)) -> CurrentUser:
    """RBAC gate: only users with role == admin may pass."""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin role required")
    return user


def ip_rate_limit(request: Request, response: Response) -> None:
    """Rate limit for unauthenticated endpoints (signup / login), keyed by client IP."""
    ip = request.client.host if request.client else "unknown"
    check_rate_limit(f"ip:{ip}", response, limit=config.LOGIN_RATE_LIMIT_MAX)


def parse_object_id(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=404, detail="Not found")
