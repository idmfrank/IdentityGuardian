from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ..services import DashboardServices


router = APIRouter()


class RiskAssessmentPayload(BaseModel):
    user_id: str


class RiskAssessmentRecord(BaseModel):
    risk_id: str
    user_id: str
    risk_score: float
    risk_level: str
    assessed_at: datetime
    details: Dict[str, Any] = Field(default_factory=dict)


class AutoBlockPayload(BaseModel):
    user_id: str
    reason: str = Field(default="High risk score exceeded policy threshold")


class AutoBlockResponse(BaseModel):
    user_id: str
    message: str
    blocked_at: datetime


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


@router.post("/assessment", response_model=RiskAssessmentRecord)
async def calculate_risk(
    payload: RiskAssessmentPayload,
    request: Request,
    services: DashboardServices = Depends(_get_services),
) -> RiskAssessmentRecord:
    store = _get_store(request)

    if services.risk_agent and not services.mock_mode:
        result = await services.risk_agent.calculate_user_risk_score(user_id=payload.user_id)
    else:
        result = await services.coordinator.process_request(
            "calculate_risk", {"user_id": payload.user_id}
        )

    risk_id = result.get("risk_id") or f"RISK-{payload.user_id}-{len(store['risk_events']) + 1:04d}"
    record = RiskAssessmentRecord(
        risk_id=risk_id,
        user_id=payload.user_id,
        risk_score=float(result.get("risk_score", 0.0)),
        risk_level=result.get("risk_level", "unknown"),
        assessed_at=datetime.utcnow(),
        details=result,
    )

    store["risk_events"][risk_id] = record
    return record


@router.get("/assessments", response_model=List[RiskAssessmentRecord])
async def list_assessments(request: Request) -> List[RiskAssessmentRecord]:
    store = _get_store(request)
    return sorted(
        store["risk_events"].values(),
        key=lambda record: record.assessed_at,
        reverse=True,
    )


@router.post("/auto-block", response_model=AutoBlockResponse)
async def auto_block(
    payload: AutoBlockPayload,
    request: Request,
    services: DashboardServices = Depends(_get_services),
) -> AutoBlockResponse:
    message = await services.identity_provider.block_via_ca(payload.user_id, payload.reason)
    return AutoBlockResponse(
        user_id=payload.user_id,
        message=message,
        blocked_at=datetime.utcnow(),
    )


@router.get("/policies")
async def list_risk_policies(
    services: DashboardServices = Depends(_get_services),
) -> Dict[str, Any]:
    policies = await services.grc_provider.get_risk_policies()
    return {"policies": policies}
