from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter()


class SCIMEvent(BaseModel):
    event_id: str
    direction: str
    payload: Dict[str, Any]
    status: str
    recorded_at: datetime
    detail: str | None = None


class SCIMLogPayload(BaseModel):
    payload: Dict[str, Any] = Field(default_factory=dict)
    status: str = "success"
    detail: str | None = None


def _get_store(request: Request) -> Dict[str, Any]:
    store = getattr(request.app.state, "data", None)
    if store is None:
        raise HTTPException(status_code=500, detail="Application store not initialised")
    return store


def _record(event_id: str, direction: str, payload: SCIMLogPayload) -> SCIMEvent:
    return SCIMEvent(
        event_id=event_id,
        direction=direction,
        payload=payload.payload,
        status=payload.status,
        detail=payload.detail,
        recorded_at=datetime.utcnow(),
    )


@router.get("/outbound", response_model=List[SCIMEvent])
async def list_outbound_logs(request: Request) -> List[SCIMEvent]:
    store = _get_store(request)
    return list(store["scim_outbound"])


@router.post("/outbound", response_model=SCIMEvent)
async def record_outbound(
    payload: SCIMLogPayload,
    request: Request,
) -> SCIMEvent:
    store = _get_store(request)
    event = _record(f"SCIM-OUT-{len(store['scim_outbound']) + 1:04d}", "outbound", payload)
    store["scim_outbound"].append(event)
    return event


@router.get("/inbound", response_model=List[SCIMEvent])
async def list_inbound_logs(request: Request) -> List[SCIMEvent]:
    store = _get_store(request)
    return list(store["scim_inbound"])


@router.post("/inbound", response_model=SCIMEvent)
async def record_inbound(
    payload: SCIMLogPayload,
    request: Request,
) -> SCIMEvent:
    store = _get_store(request)
    event = _record(f"SCIM-IN-{len(store['scim_inbound']) + 1:04d}", "inbound", payload)
    store["scim_inbound"].append(event)
    return event
