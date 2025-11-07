from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ..services import DashboardServices


router = APIRouter()


class GroupRecord(BaseModel):
    group_id: str
    display_name: str
    members: List[str] = Field(default_factory=list)
    created_at: datetime
    role: str | None = None


class GroupCreatePayload(BaseModel):
    display_name: str
    role: str | None = None


class GroupMembersPayload(BaseModel):
    members: List[str] = Field(default_factory=list)


def _get_store(request: Request) -> Dict[str, Any]:
    store = getattr(request.app.state, "data", None)
    if store is None:
        raise HTTPException(status_code=500, detail="Application store not initialised")
    return store


def _get_services(request: Request) -> DashboardServices:
    services = getattr(request.app.state, "services", None)
    if services is None:
        raise HTTPException(status_code=500, detail="Service container not initialised")
    return services


def _group_from_store(key: str, value: Dict[str, Any]) -> GroupRecord:
    return GroupRecord(
        group_id=key,
        display_name=value.get("displayName", key),
        members=value.get("members", []),
        created_at=value.get("createdAt", datetime.utcnow()),
        role=value.get("role"),
    )


@router.get("/", response_model=List[GroupRecord])
async def list_groups(request: Request) -> List[GroupRecord]:
    store = _get_store(request)
    return [
        _group_from_store(group_id, data)
        for group_id, data in store["groups"].items()
    ]


@router.post("/", response_model=GroupRecord)
async def create_group(
    payload: GroupCreatePayload,
    request: Request,
    services: DashboardServices = Depends(_get_services),
) -> GroupRecord:
    store = _get_store(request)
    group_id = payload.role or f"group-{uuid.uuid4()}"
    display_name = payload.display_name

    if group_id in store["groups"]:
        raise HTTPException(status_code=400, detail="Group already exists")

    group_entry = {
        "displayName": display_name,
        "members": [],
        "createdAt": datetime.utcnow(),
        "role": payload.role,
    }
    store["groups"][group_id] = group_entry

    if services.mock_mode and hasattr(services.identity_provider, "access_assignments"):
        services.identity_provider.access_assignments.setdefault(group_id, [])

    return _group_from_store(group_id, group_entry)


@router.post("/{group_id}/members", response_model=GroupRecord)
async def add_members(
    group_id: str,
    payload: GroupMembersPayload,
    request: Request,
) -> GroupRecord:
    store = _get_store(request)
    entry = store["groups"].get(group_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Group not found")

    existing = set(entry.get("members", []))
    existing.update(payload.members)
    entry["members"] = sorted(existing)
    store["groups"][group_id] = entry

    return _group_from_store(group_id, entry)


@router.delete("/{group_id}/members/{user_id}", response_model=GroupRecord)
async def remove_member(group_id: str, user_id: str, request: Request) -> GroupRecord:
    store = _get_store(request)
    entry = store["groups"].get(group_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Group not found")

    entry["members"] = [member for member in entry.get("members", []) if member != user_id]
    store["groups"][group_id] = entry
    return _group_from_store(group_id, entry)


@router.delete("/{group_id}")
async def delete_group(group_id: str, request: Request) -> Dict[str, str]:
    store = _get_store(request)
    if group_id not in store["groups"]:
        raise HTTPException(status_code=404, detail="Group not found")

    del store["groups"][group_id]
    return {"status": "deleted", "group_id": group_id}
