"""Tenants, authentication and user management."""
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.errors import DuplicateKeyError

from .db import get_db
from .deps import CurrentUser, ip_rate_limit, rate_limited_user, require_admin
from .schemas import LoginRequest, TenantCreate, TokenResponse, UserCreate, UserOut
from .security import create_access_token, hash_password, verify_password

router = APIRouter()


def _user_out(doc) -> UserOut:
    return UserOut(id=str(doc["_id"]), tenant_id=doc["tenant_id"], username=doc["username"], role=doc["role"])


@router.post("/tenants", status_code=status.HTTP_201_CREATED, tags=["tenants"], dependencies=[Depends(ip_rate_limit)])
def create_tenant(body: TenantCreate):
    """Self-service signup: creates a tenant and its first admin user."""
    db = get_db()
    now = datetime.now(timezone.utc)
    try:
        db.tenants.insert_one({"tenant_id": body.tenant_id, "name": body.name, "created_at": now})
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail="Tenant already exists")
    res = db.users.insert_one(
        {
            "tenant_id": body.tenant_id,
            "username": body.admin_username,
            "password_hash": hash_password(body.admin_password),
            "role": "admin",
            "created_at": now,
        }
    )
    return {"tenant_id": body.tenant_id, "name": body.name, "admin_user_id": str(res.inserted_id)}


@router.post("/auth/login", response_model=TokenResponse, tags=["auth"], dependencies=[Depends(ip_rate_limit)])
def login(body: LoginRequest):
    user = get_db().users.find_one({"tenant_id": body.tenant_id, "username": body.username})
    # same error for "no such user" and "wrong password" -> no user enumeration
    if user is None or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(str(user["_id"]), user["tenant_id"], user["role"])
    return TokenResponse(access_token=token, tenant_id=user["tenant_id"], role=user["role"])


@router.get("/me", response_model=UserOut, tags=["auth"])
def me(user: CurrentUser = Depends(rate_limited_user)):
    return UserOut(id=user.id, tenant_id=user.tenant_id, username=user.username, role=user.role)


@router.post("/users", response_model=UserOut, status_code=201, tags=["users (admin)"])
def create_user(body: UserCreate, admin: CurrentUser = Depends(require_admin)):
    """Admin creates a user *inside their own tenant* (tenant comes from the JWT)."""
    doc = {
        "tenant_id": admin.tenant_id,
        "username": body.username,
        "password_hash": hash_password(body.password),
        "role": body.role,
        "created_at": datetime.now(timezone.utc),
    }
    try:
        res = get_db().users.insert_one(doc)
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail="Username already exists in this tenant")
    doc["_id"] = res.inserted_id
    return _user_out(doc)


@router.get("/users", response_model=List[UserOut], tags=["users (admin)"])
def list_users(admin: CurrentUser = Depends(require_admin)):
    return [_user_out(u) for u in get_db().users.find({"tenant_id": admin.tenant_id}).sort("username", 1)]
