from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ..services import DashboardServices


router = APIRouter()


class BehaviorAnalysisPayload(BaseModel):
    user_id: str


class BehaviorAnalysisRecord(BaseModel):
    user_id: str
    analyzed_at: datetime
    anomalies_detected: int
    details: Dict[str, Any] = Field(default_factory=dict)


class DormantAccountRecord(BaseModel):
    user_id: str
    username: str
    department: str
    last_activity: str
    recommendation: str


class DormantResponse(BaseModel):
    dormant_accounts_found: int
    accounts: List[DormantAccountRecord]
    total_users_scanned: int


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


@router.post("/analyze", response_model=BehaviorAnalysisRecord)
async def analyze_user_behavior(
    payload: BehaviorAnalysisPayload,
    request: Request,
    services: DashboardServices = Depends(_get_services),
) -> BehaviorAnalysisRecord:
    store = _get_store(request)

    if services.monitoring_agent and not services.mock_mode:
        result = await services.monitoring_agent.analyze_user_behavior(user_id=payload.user_id)
    else:
        result = await services.coordinator.process_request(
            "analyze_behavior", {"user_id": payload.user_id}
        )

    anomalies = result.get("anomalies", [])
    record = BehaviorAnalysisRecord(
        user_id=payload.user_id,
        analyzed_at=datetime.utcnow(),
        anomalies_detected=result.get("anomalies_detected", len(anomalies)),
        details=result,
    )

    store["monitoring_alerts"].append(record)
    return record


@router.get("/alerts", response_model=List[BehaviorAnalysisRecord])
async def list_alerts(request: Request) -> List[BehaviorAnalysisRecord]:
    store = _get_store(request)
    return sorted(
        store["monitoring_alerts"],
        key=lambda alert: alert.analyzed_at,
        reverse=True,
    )


@router.get("/dormant", response_model=DormantResponse)
async def detect_dormant_accounts(
    request: Request,
    services: DashboardServices = Depends(_get_services),
) -> DormantResponse:
    if services.monitoring_agent and not services.mock_mode:
        result = await services.monitoring_agent.detect_dormant_accounts()
    else:
        result = await services.coordinator.process_request("detect_dormant_accounts", {})

    accounts = [
        DormantAccountRecord(**account)
        for account in result.get("accounts", [])
    ]

    return DormantResponse(
        dormant_accounts_found=result.get("dormant_accounts_found", len(accounts)),
        accounts=accounts,
        total_users_scanned=result.get("total_users_scanned", 0),
    )
