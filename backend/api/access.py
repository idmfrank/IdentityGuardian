from __future__ import annotations
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ..services import DashboardServices


router = APIRouter()


class AccessRequestPayload(BaseModel):
    user_id: str = Field(..., description="User principal name or ID making the request")
    resource_id: str = Field(..., alias="resource", description="Target resource identifier")
    access_level: str = Field("member", description="Requested access level or role")
    business_justification: str = Field(..., alias="justification", description="Reason for the request")
    resource_type: str = Field("application", description="Resource category for reporting")

    class Config:
        populate_by_name = True


class AccessRequestRecord(BaseModel):
    request_id: str
    submitted_at: datetime
    status: str
    risk_score: float | None = None
    approvers: List[str] = Field(default_factory=list)
    ticket_id: str | None = None
    recommendation: str | None = None
    policy_violations: List[str] | None = None
    user_id: str
    resource_id: str
    access_level: str
    business_justification: str


class AccessApprovalPayload(BaseModel):
    approver_id: str


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


@router.post("/request", response_model=AccessRequestRecord)
async def submit_request(
    payload: AccessRequestPayload,
    request: Request,
    services: DashboardServices = Depends(_get_services),
) -> AccessRequestRecord:
    store = _get_store(request)

    if services.access_request_agent and not services.mock_mode:
        result = await services.access_request_agent.handle_request(payload.model_dump(by_alias=False))
    else:
        result = await services.coordinator.process_request(
            "access_request",
            {
                "user_id": payload.user_id,
                "resource_id": payload.resource_id,
                "resource_type": payload.resource_type,
                "access_level": payload.access_level,
                "business_justification": payload.business_justification,
            },
        )

    request_id = result.get("request_id") or f"REQ-{len(store['access_requests']) + 1:04d}"
    record = AccessRequestRecord(
        request_id=request_id,
        submitted_at=datetime.utcnow(),
        status=result.get("status", "pending"),
        risk_score=result.get("risk_score"),
        approvers=result.get("approvers", []),
        ticket_id=result.get("ticket_id"),
        recommendation=result.get("recommendation"),
        policy_violations=result.get("policy_violations"),
        user_id=payload.user_id,
        resource_id=payload.resource_id,
        access_level=payload.access_level,
        business_justification=payload.business_justification,
    )

    store["access_requests"][request_id] = record
    return record


@router.get("/requests", response_model=List[AccessRequestRecord])
async def list_requests(request: Request) -> List[AccessRequestRecord]:
    store = _get_store(request)
    return sorted(
        store["access_requests"].values(),
        key=lambda rec: rec.submitted_at,
        reverse=True,
    )


@router.post("/requests/{request_id}/approve", response_model=AccessRequestRecord)
async def approve_request(
    request_id: str,
    payload: AccessApprovalPayload,
    request: Request,
    services: DashboardServices = Depends(_get_services),
) -> AccessRequestRecord:
    store = _get_store(request)
    record = store["access_requests"].get(request_id)
    if not record:
        raise HTTPException(status_code=404, detail="Access request not found")

    if services.access_request_agent and not services.mock_mode:
        result = await services.coordinator.process_request(
            "approve_request",
            {"request_id": request_id, "approver_id": payload.approver_id},
        )
        record.status = result.get("status", "approved")
    else:
        record.status = "approved"

    store["access_requests"][request_id] = record
    return record
