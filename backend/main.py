from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import access, groups, lifecycle, monitoring, reviews, risk, scim
from .services import DashboardServices, init_services


def _initial_data(services: DashboardServices) -> Dict[str, Any]:
    """Seed in-memory collections that back the dashboard endpoints."""

    settings = services.settings
    role_groups = {
        role: {
            "displayName": f"{settings.SCIM_GROUP_PREFIX or ''}{group}",
            "members": [],
            "createdAt": datetime.utcnow(),
        }
        for role, group in settings.ROLE_TO_GROUP_MAP.items()
    }

    return {
        "access_requests": {},
        "review_campaigns": {},
        "review_items": {},
        "lifecycle_events": [],
        "monitoring_alerts": [],
        "risk_events": {},
        "scim_outbound": [],
        "scim_inbound": [],
        "groups": role_groups,
    }


app = FastAPI(title="IdentityGuardian Dashboard")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup() -> None:
    services = await init_services()
    app.state.services = services
    app.state.data = _initial_data(services)


@app.get("/")
async def root() -> Dict[str, str]:
    return {"message": "IdentityGuardian API"}


app.include_router(access.router, prefix="/api/access")
app.include_router(reviews.router, prefix="/api/reviews")
app.include_router(lifecycle.router, prefix="/api/lifecycle")
app.include_router(risk.router, prefix="/api/risk")
app.include_router(monitoring.router, prefix="/api/monitoring")
app.include_router(scim.router, prefix="/api/scim")
app.include_router(groups.router, prefix="/api/groups")
