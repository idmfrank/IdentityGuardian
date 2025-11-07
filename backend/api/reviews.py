from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ..services import DashboardServices


router = APIRouter()


class CampaignCreatePayload(BaseModel):
    campaign_name: str
    scope: str
    duration_days: int = Field(default=30, ge=1, le=180)


class ReviewItemRecord(BaseModel):
    review_item_id: str
    campaign_id: str
    user_id: str
    resource_id: str
    access_level: str
    reviewer_id: str
    status: str
    recommendation: str | None = None
    risk_score: float = 0.0
    last_used: datetime | None = None
    assigned_date: datetime | None = None


class ReviewCampaignRecord(BaseModel):
    campaign_id: str
    campaign_name: str
    scope: str
    start_date: datetime
    end_date: datetime
    created_at: datetime
    created_by: str
    status: str
    review_items: List[ReviewItemRecord] = Field(default_factory=list)


class ReviewDecisionPayload(BaseModel):
    decision: str
    reviewer_id: str
    justification: str | None = None


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


def _campaign_from_agent(campaign) -> ReviewCampaignRecord:
    items = []
    for item in campaign.review_items:
        items.append(
            ReviewItemRecord(
                review_item_id=item.review_item_id,
                campaign_id=item.campaign_id,
                user_id=item.user_id,
                resource_id=item.resource_id,
                access_level=item.access_level,
                reviewer_id=item.reviewer_id,
                status=str(item.status),
                recommendation=item.recommendation,
                risk_score=item.risk_score,
                last_used=item.last_used,
                assigned_date=item.assigned_date,
            )
        )

    return ReviewCampaignRecord(
        campaign_id=campaign.campaign_id,
        campaign_name=campaign.campaign_name,
        scope=campaign.scope,
        start_date=campaign.start_date,
        end_date=campaign.end_date,
        created_at=campaign.created_at,
        created_by=campaign.created_by,
        status=campaign.status,
        review_items=items,
    )


async def _generate_mock_items(
    services: DashboardServices,
    campaign_id: str,
) -> List[ReviewItemRecord]:
    users = await services.identity_provider.list_users()
    items: List[ReviewItemRecord] = []

    for user in users:
        assignments = await services.identity_provider.get_user_access(user.user_id)
        if not assignments:
            assignments = [
                {
                    "resource_id": f"{user.department.lower()}_workspace",
                    "access_level": "read",
                    "granted_at": datetime.utcnow() - timedelta(days=45),
                }
            ]

        for access in assignments:
            compliance = await services.grc_provider.check_policy_compliance(
                user.user_id,
                access.get("resource_id", "unknown"),
                access.get("access_level", "member"),
            )
            risk_score = 0.25
            if not compliance.get("compliant", True):
                risk_score += 0.25
            if "admin" in access.get("access_level", "").lower():
                risk_score += 0.2

            recommendation = "REVOKE" if risk_score >= 0.6 else "APPROVE"

            items.append(
                ReviewItemRecord(
                    review_item_id=f"REV-{uuid.uuid4()}",
                    campaign_id=campaign_id,
                    user_id=user.user_id,
                    resource_id=access.get("resource_id", "unknown"),
                    access_level=access.get("access_level", "member"),
                    reviewer_id=user.manager_id or "manager",
                    status="pending",
                    recommendation=recommendation,
                    risk_score=round(risk_score, 2),
                    last_used=access.get("granted_at"),
                    assigned_date=access.get("granted_at", datetime.utcnow()),
                )
            )

        if len(items) >= 20:
            break

    return items


@router.post("/campaigns", response_model=ReviewCampaignRecord)
async def create_campaign(
    payload: CampaignCreatePayload,
    request: Request,
    services: DashboardServices = Depends(_get_services),
) -> ReviewCampaignRecord:
    store = _get_store(request)

    if services.access_review_agent and not services.mock_mode:
        summary = await services.access_review_agent.create_campaign(
            campaign_name=payload.campaign_name,
            scope=payload.scope,
            duration_days=payload.duration_days,
        )
        campaign = services.access_review_agent.campaigns[summary["campaign_id"]]
        record = _campaign_from_agent(campaign)
    else:
        campaign_id = f"CAM-{uuid.uuid4()}"
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=payload.duration_days)
        items = await _generate_mock_items(services, campaign_id)
        record = ReviewCampaignRecord(
            campaign_id=campaign_id,
            campaign_name=payload.campaign_name,
            scope=payload.scope,
            start_date=start_date,
            end_date=end_date,
            created_at=start_date,
            created_by="system",
            status="active",
            review_items=items,
        )

    store["review_campaigns"][record.campaign_id] = record
    store["review_items"][record.campaign_id] = {
        item.review_item_id: item for item in record.review_items
    }
    return record


@router.get("/campaigns", response_model=List[ReviewCampaignRecord])
async def list_campaigns(request: Request) -> List[ReviewCampaignRecord]:
    store = _get_store(request)
    return sorted(
        store["review_campaigns"].values(),
        key=lambda camp: camp.start_date,
        reverse=True,
    )


@router.get("/campaigns/{campaign_id}", response_model=ReviewCampaignRecord)
async def get_campaign(campaign_id: str, request: Request) -> ReviewCampaignRecord:
    store = _get_store(request)
    record = store["review_campaigns"].get(campaign_id)
    if not record:
        raise HTTPException(status_code=404, detail="Review campaign not found")
    return record


@router.post(
    "/campaigns/{campaign_id}/items/{review_item_id}",
    response_model=ReviewItemRecord,
)
async def submit_review_decision(
    campaign_id: str,
    review_item_id: str,
    payload: ReviewDecisionPayload,
    request: Request,
    services: DashboardServices = Depends(_get_services),
) -> ReviewItemRecord:
    store = _get_store(request)
    campaign_items: Dict[str, ReviewItemRecord] = store["review_items"].setdefault(campaign_id, {})
    item = campaign_items.get(review_item_id)

    if services.access_review_agent and not services.mock_mode:
        result = await services.access_review_agent.process_review_decision(
            campaign_id=campaign_id,
            review_item_id=review_item_id,
            decision=payload.decision,
            reviewer_id=payload.reviewer_id,
            justification=payload.justification or "",
        )
        if not result.get("success", True):
            raise HTTPException(status_code=400, detail=result.get("reason", "Decision failed"))
        campaign = services.access_review_agent.campaigns.get(campaign_id)
        if campaign:
            updated = next(
                (ri for ri in campaign.review_items if ri.review_item_id == review_item_id),
                None,
            )
            if updated:
                item = ReviewItemRecord(
                    review_item_id=updated.review_item_id,
                    campaign_id=updated.campaign_id,
                    user_id=updated.user_id,
                    resource_id=updated.resource_id,
                    access_level=updated.access_level,
                    reviewer_id=updated.reviewer_id,
                    status=str(updated.status),
                    recommendation=updated.recommendation,
                    risk_score=updated.risk_score,
                    last_used=updated.last_used,
                    assigned_date=updated.assigned_date,
                )
    else:
        if not item:
            raise HTTPException(status_code=404, detail="Review item not found")
        item.status = payload.decision.lower()
        item.recommendation = payload.decision.upper()

    if item is None:
        raise HTTPException(status_code=404, detail="Review item not found")

    campaign_items[review_item_id] = item
    store["review_items"][campaign_id] = campaign_items
    if campaign_id in store["review_campaigns"]:
        campaign_record = store["review_campaigns"][campaign_id]
        updated_items = [campaign_items[i.review_item_id] for i in campaign_record.review_items]
        campaign_record.review_items = updated_items
        store["review_campaigns"][campaign_id] = campaign_record

    return item
