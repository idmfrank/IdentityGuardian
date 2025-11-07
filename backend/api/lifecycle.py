from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from identity_guardian.models.identity import LifecycleEventType, User, UserStatus

from ..services import DashboardServices


router = APIRouter()


class JoinerPayload(BaseModel):
    user_id: str
    username: str
    email: str
    first_name: str
    last_name: str
    department: str
    manager_id: str | None = None
    roles: List[str] = Field(default_factory=list)
    start_date: datetime = Field(default_factory=datetime.utcnow)


class MoverPayload(BaseModel):
    user_id: str
    new_department: str
    new_role: str
    effective_date: datetime = Field(default_factory=datetime.utcnow)


class LeaverPayload(BaseModel):
    user_id: str
    termination_date: datetime = Field(default_factory=datetime.utcnow)
    reason: str | None = None


class LifecycleEventRecord(BaseModel):
    event_id: str
    event_type: str
    user_id: str
    status: str
    triggered_at: datetime
    effective_date: datetime
    details: Dict[str, Any] = Field(default_factory=dict)


def _get_services(request: Request) -> DashboardServices:
    services = getattr(request.app.state, "services", None)
    if services is None:
        raise HTTPException(status_code=500, detail="Service container not initialised")
    return services


def _get_store(request: Request) -> Dict[str, Any]:
    store = getattr(request.app.state, "data", None)
    if store is None:
        raise HTTPException(status_code=500, detail="Application store not initialised")
    return store


def _user_from_payload(payload: JoinerPayload) -> User:
    return User(
        user_id=payload.user_id,
        username=payload.username,
        email=payload.email,
        first_name=payload.first_name,
        last_name=payload.last_name,
        department=payload.department,
        manager_id=payload.manager_id,
        roles=payload.roles,
        status=UserStatus.ACTIVE,
        hire_date=payload.start_date,
    )


async def _mock_joiner(services: DashboardServices, user: User, start_date: datetime) -> Dict[str, Any]:
    provisioning_tasks = [
        "Create identity provider account",
        f"Grant baseline access for {user.department}",
        "Configure MFA and conditional access",
        "Notify manager of onboarding completion",
    ]

    if "engineer" in user.department.lower():
        provisioning_tasks.append("Provision source control access")

    ticket_id = await services.itsm_provider.create_ticket(
        title=f"Onboard {user.first_name} {user.last_name}",
        description=f"Provision access for department {user.department}",
        category="Provisioning",
        priority="High",
    )

    return {
        "event_id": f"LC-{uuid.uuid4()}",
        "event_type": LifecycleEventType.JOINER.value,
        "user_id": user.user_id,
        "status": "completed",
        "provisioning_tasks": provisioning_tasks,
        "ticket_id": ticket_id,
        "effective_date": start_date,
    }


async def _mock_mover(
    services: DashboardServices,
    payload: MoverPayload,
) -> Dict[str, Any]:
    provisioning_tasks = [f"Grant {payload.new_role} baseline entitlements"]
    deprovisioning_tasks = ["Remove obsolete access from previous role"]

    ticket_id = await services.itsm_provider.create_ticket(
        title=f"Role change for {payload.user_id}",
        description=f"Transition to {payload.new_role} in {payload.new_department}",
        category="Access Change",
        priority="Medium",
    )

    return {
        "event_id": f"LC-{uuid.uuid4()}",
        "event_type": LifecycleEventType.MOVER.value,
        "user_id": payload.user_id,
        "status": "completed",
        "provisioning_tasks": provisioning_tasks,
        "deprovisioning_tasks": deprovisioning_tasks,
        "ticket_id": ticket_id,
        "effective_date": payload.effective_date,
        "new_department": payload.new_department,
        "new_role": payload.new_role,
    }


async def _mock_leaver(
    services: DashboardServices,
    payload: LeaverPayload,
) -> Dict[str, Any]:
    deprovisioning_tasks = [
        "Disable identity provider account",
        "Revoke privileged access",
        "Archive mailbox and OneDrive",
        "Remove from distribution lists",
    ]

    ticket_id = await services.itsm_provider.create_ticket(
        title=f"Offboard {payload.user_id}",
        description="Terminate access and disable accounts",
        category="Deprovisioning",
        priority="High",
    )

    return {
        "event_id": f"LC-{uuid.uuid4()}",
        "event_type": LifecycleEventType.LEAVER.value,
        "user_id": payload.user_id,
        "status": "completed",
        "deprovisioning_tasks": deprovisioning_tasks,
        "ticket_id": ticket_id,
        "effective_date": payload.termination_date,
        "reason": payload.reason or "",
    }


def _record_from_result(result: Dict[str, Any]) -> LifecycleEventRecord:
    return LifecycleEventRecord(
        event_id=result.get("event_id", f"LC-{uuid.uuid4()}"),
        event_type=result.get("event_type", "unknown"),
        user_id=result.get("user_id", ""),
        status=result.get("status", "pending"),
        triggered_at=datetime.utcnow(),
        effective_date=result.get("effective_date", datetime.utcnow()),
        details={k: v for k, v in result.items() if k not in {"event_id", "event_type", "user_id", "status"}},
    )


@router.post("/joiner", response_model=LifecycleEventRecord)
async def process_joiner(
    payload: JoinerPayload,
    request: Request,
    services: DashboardServices = Depends(_get_services),
) -> LifecycleEventRecord:
    store = _get_store(request)
    user = _user_from_payload(payload)

    if services.lifecycle_agent and not services.mock_mode:
        result = await services.lifecycle_agent.process_joiner(user=user, start_date=payload.start_date)
    else:
        result = await _mock_joiner(services, user, payload.start_date)

    record = _record_from_result(result)
    store["lifecycle_events"].append(record)
    return record


@router.post("/mover", response_model=LifecycleEventRecord)
async def process_mover(
    payload: MoverPayload,
    request: Request,
    services: DashboardServices = Depends(_get_services),
) -> LifecycleEventRecord:
    store = _get_store(request)

    if services.lifecycle_agent and not services.mock_mode:
        result = await services.lifecycle_agent.process_mover(
            user_id=payload.user_id,
            new_department=payload.new_department,
            new_role=payload.new_role,
            effective_date=payload.effective_date,
        )
        if not result.get("success", True) and "event_id" not in result:
            raise HTTPException(status_code=400, detail=result.get("reason", "Mover failed"))
    else:
        result = await _mock_mover(services, payload)

    record = _record_from_result(result)
    store["lifecycle_events"].append(record)
    return record


@router.post("/leaver", response_model=LifecycleEventRecord)
async def process_leaver(
    payload: LeaverPayload,
    request: Request,
    services: DashboardServices = Depends(_get_services),
) -> LifecycleEventRecord:
    store = _get_store(request)

    if services.lifecycle_agent and not services.mock_mode:
        result = await services.lifecycle_agent.process_leaver(
            user_id=payload.user_id,
            termination_date=payload.termination_date,
        )
        if not result.get("success", True) and "event_id" not in result:
            raise HTTPException(status_code=400, detail=result.get("reason", "Leaver failed"))
    else:
        result = await _mock_leaver(services, payload)

    record = _record_from_result(result)
    store["lifecycle_events"].append(record)
    return record


@router.get("/events", response_model=List[LifecycleEventRecord])
async def list_events(request: Request) -> List[LifecycleEventRecord]:
    store = _get_store(request)
    return sorted(
        store["lifecycle_events"],
        key=lambda event: event.triggered_at,
        reverse=True,
    )
