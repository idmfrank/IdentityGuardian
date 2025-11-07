"""FastAPI webhook endpoint for Teams adaptive card responses."""

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import FastAPI, Request

from identity_guardian.config.settings import get_graph_client
from identity_guardian.integrations.identity_provider import get_identity_provider
from identity_guardian.integrations.teams_bot import TeamsApprovalBot


app = FastAPI()
logger = logging.getLogger(__name__)


def _extract_action(payload: Dict[str, Any]) -> Dict[str, Any]:
    value = payload.get("value") or {}
    data = value.get("data") if isinstance(value, dict) else {}
    return data if isinstance(data, dict) else {}


@app.post("/webhook/teams")
async def teams_webhook(request: Request):
    payload = await request.json()
    logger.debug("Received Teams webhook payload: %s", payload)

    if payload.get("type") != "message":
        return {"text": "Ignored."}

    action = _extract_action(payload)
    if not action:
        return {"text": "No action data provided."}

    decision = action.get("action")

    if not decision:
        return {"text": "Missing action."}

    if decision == "re_enable":
        user_id = action.get("user_id")
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

    request_id = action.get("request_id")
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

