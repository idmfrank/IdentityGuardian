"""FastAPI webhook endpoint for Teams adaptive card responses."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from functools import wraps

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from identity_guardian.config.settings import get_graph_client, get_settings
from identity_guardian.integrations.identity_provider import get_identity_provider
from identity_guardian.integrations.teams_bot import TeamsApprovalBot


app = FastAPI()
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):  # pragma: no cover - simple handler
    return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
logger = logging.getLogger(__name__)
settings = get_settings()


class TeamsAction(BaseModel):
    action: Optional[str] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None


class TeamsWebhookPayload(BaseModel):
    type: str
    value: Dict[str, Any] | None = None

    def extract_action(self) -> TeamsAction:
        payload = {}
        if isinstance(self.value, dict):
            inner = self.value.get("data")
            if isinstance(inner, dict):
                payload = inner
        return TeamsAction.model_validate(payload)


def _optional_rate_limit(limit: str):
    """Apply rate limiting when a real FastAPI/Starlette request is provided."""

    def decorator(func):
        limited = limiter.limit(limit)(func)

        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get("request")
            if request is None and args:
                request = args[0]

            if isinstance(request, Request):
                return await limited(*args, **kwargs)

            return await func(*args, **kwargs)

        return wrapper

    return decorator


@app.post("/webhook/teams")
@_optional_rate_limit("10/minute")
async def teams_webhook(request: Request, csrf_token: str | None = Header(default=None, alias="X-CSRF-Token")):
    if settings.TEAMS_WEBHOOK_SECRET and csrf_token != settings.TEAMS_WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid CSRF token")

    raw_payload = await request.json()
    logger.debug("Received Teams webhook payload: %s", raw_payload)

    try:
        payload = TeamsWebhookPayload.model_validate(raw_payload)
    except ValidationError as exc:
        logger.warning("Rejected Teams webhook due to validation error: %s", exc)
        raise HTTPException(status_code=400, detail="Invalid payload")

    if payload.type != "message":
        return {"text": "Ignored."}

    action = payload.extract_action()
    if not action.action:
        return {"text": "Missing action."}

    decision = action.action

    if decision == "re_enable":
        user_id = action.user_id
        if not user_id:
            return {"text": "Missing user identifier."}

        provider = await get_identity_provider()
        result = await provider.remove_ca_block(user_id)

        bot = TeamsApprovalBot()
        try:
            await bot.send_alert(user_id, "Access restored after investigation.", 0)
        except Exception as exc:  # pragma: no cover - notification failures shouldn't block webhook
            logger.warning("Failed to send restoration alert for %s: %s", user_id, exc)

        return {"text": result}

    if decision == "keep_blocked":
        return {"text": "User remains blocked pending investigation."}

    request_id = action.request_id
    if not request_id:
        return {"text": "Missing approval context."}

    client = await get_graph_client()
    if client is None:
        logger.error("Graph client not available for processing Teams webhook")
        return {"text": "Graph client unavailable."}

    try:
        if decision == "approve":
            body = {"action": "adminApprove"}
            await client.identity_governance.privileged_access.role_assignment_requests.by_role_assignment_request_id(request_id).post(body)
            logger.info("PIM request %s approved via Teams.", request_id)
            return {"text": "Access approved and activated!"}

        body = {"action": "adminReject", "justification": "Rejected via Teams"}
        await client.identity_governance.privileged_access.role_assignment_requests.by_role_assignment_request_id(request_id).post(body)
        logger.info("PIM request %s rejected via Teams.", request_id)
        return {"text": "Request rejected."}
    except Exception as exc:
        logger.error("Failed to process PIM decision for %s: %s", request_id, exc, exc_info=True)
        return {"text": "Error processing request."}

