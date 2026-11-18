"""
Task CRUD with tenant isolation + RBAC (Lab 15.1, tasks 2 and Activity).

Isolation rule : EVERY query contains {"tenant_id": <from JWT>}.
RBAC rule      : role == admin -> all tasks of the tenant
                 role == user  -> only tasks where owner_id == their own id
Both rules live in ONE helper (`scope_filter`) so no endpoint can forget them.
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pymongo import DESCENDING, ReturnDocument

from .db import get_db
from .deps import CurrentUser, parse_object_id, rate_limited_user
from .schemas import Priority, Status, TaskCreate, TaskList, TaskOut, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"])


def scope_filter(user: CurrentUser, task_id: Optional[str] = None) -> dict:
    flt: dict = {"tenant_id": user.tenant_id}          # tenant isolation
    if not user.is_admin:
        flt["owner_id"] = user.id                      # RBAC: regular users see only their own
    if task_id is not None:
        flt["_id"] = parse_object_id(task_id)
    return flt


def to_out(doc) -> TaskOut:
    return TaskOut(
        id=str(doc["_id"]),
        tenant_id=doc["tenant_id"],
        owner_id=doc["owner_id"],
        title=doc["title"],
        description=doc.get("description", ""),
        priority=doc["priority"],
        status=doc["status"],
        created_at=doc["created_at"],
        updated_at=doc.get("updated_at", doc["created_at"]),
    )


@router.post("/", response_model=TaskOut, status_code=201)
def create_task(body: TaskCreate, user: CurrentUser = Depends(rate_limited_user)):
    now = datetime.now(timezone.utc)
    doc = {
        "tenant_id": user.tenant_id,
        "owner_id": user.id,
        "title": body.title,
        "description": body.description,
        "priority": body.priority,
        "status": "open",
        "created_at": now,
        "updated_at": now,
    }
    doc["_id"] = get_db().tasks.insert_one(doc).inserted_id
    return to_out(doc)


@router.get("/", response_model=TaskList)
def list_tasks(
    status: Optional[Status] = None,
    priority: Optional[Priority] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user: CurrentUser = Depends(rate_limited_user),
):
    flt = scope_filter(user)
    if status:
        flt["status"] = status
    if priority:
        flt["priority"] = priority
    coll = get_db().tasks
    items = coll.find(flt).sort("created_at", DESCENDING).skip(skip).limit(limit)
    return TaskList(total=coll.count_documents(flt), skip=skip, limit=limit, items=[to_out(d) for d in items])


@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: str, user: CurrentUser = Depends(rate_limited_user)):
    doc = get_db().tasks.find_one(scope_filter(user, task_id))
    if doc is None:  # 404 (not 403) so other tenants'/users' task ids can't be probed
        raise HTTPException(status_code=404, detail="Task not found")
    return to_out(doc)


@router.put("/{task_id}", response_model=TaskOut)
@router.patch("/{task_id}", response_model=TaskOut)
def update_task(task_id: str, body: TaskUpdate, user: CurrentUser = Depends(rate_limited_user)):
    changes = body.model_dump(exclude_unset=True, exclude_none=True)
    if not changes:
        raise HTTPException(status_code=400, detail="No fields to update")
    changes["updated_at"] = datetime.now(timezone.utc)
    doc = get_db().tasks.find_one_and_update(
        scope_filter(user, task_id), {"$set": changes}, return_document=ReturnDocument.AFTER
    )
    if doc is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return to_out(doc)


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: str, user: CurrentUser = Depends(rate_limited_user)):
    res = get_db().tasks.delete_one(scope_filter(user, task_id))
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    return Response(status_code=204)
