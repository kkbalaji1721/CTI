from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

Priority = Literal["low", "medium", "high"]
Status = Literal["open", "in_progress", "done"]
Role = Literal["admin", "user"]


class TenantCreate(BaseModel):
    tenant_id: str = Field(pattern=r"^[a-z0-9_]{3,32}$", examples=["acme"])
    name: str = Field(min_length=1, max_length=100, examples=["Acme Corp"])
    admin_username: str = Field(min_length=3, max_length=50, examples=["admin"])
    admin_password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    tenant_id: str
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    tenant_id: str
    role: Role


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)
    role: Role = "user"


class UserOut(BaseModel):
    id: str
    tenant_id: str
    username: str
    role: Role


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=5000)
    priority: Priority = "medium"


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=5000)
    priority: Optional[Priority] = None
    status: Optional[Status] = None


class TaskOut(BaseModel):
    id: str
    tenant_id: str
    owner_id: str
    title: str
    description: str
    priority: Priority
    status: Status
    created_at: datetime
    updated_at: datetime


class TaskList(BaseModel):
    total: int
    skip: int
    limit: int
    items: List[TaskOut]
