"""Microsoft Teams approval bot integration for adaptive card approvals."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

import aiohttp

from ..config.settings import get_settings


logger = logging.getLogger(__name__)


class TeamsApprovalBot:
    """Simple helper for sending adaptive approval cards into Microsoft Teams."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self.bot_id: str = getattr(self._settings, "BOT_ID", "")
        self.bot_password: str = getattr(self._settings, "BOT_PASSWORD", "")
        self.conversation_id: str = getattr(self._settings, "TEAMS_CHANNEL_ID", "")
        self.service_url = "https://smba.trafficmanager.net/amer/"
        self._token: Optional[str] = None

    async def _get_token(self) -> str:
        if self._token:
            return self._token

        if not self.bot_id or not self.bot_password:
            raise ValueError("BOT_ID and BOT_PASSWORD must be configured to use TeamsApprovalBot")

        url = "https://login.microsoftonline.com/botframework.com/oauth2/v2.0/token"
        data = {
            "grant_type": "client_credentials",
            "client_id": self.bot_id,
            "client_secret": self.bot_password,
            "scope": "https://api.botframework.com/.default",
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data) as resp:
                payload = await resp.json()
                token = payload.get("access_token")
                if not token:
                    message = json.dumps(payload)
                    raise ValueError(f"Unable to obtain bot access token: {message}")
                self._token = token
                return token

    async def send_approval_card(
        self,
        user_id: str,
        resource: str,
        justification: str,
        pim_request_id: str,
    ) -> Dict[str, Any]:
        """Send an adaptive approval card with Approve/Reject actions."""

        if not self.conversation_id:
            raise ValueError("TEAMS_CHANNEL_ID must be configured to send Teams approval cards")

        token = await self._get_token()

        card = {
            "type": "AdaptiveCard",
            "version": "1.5",
            "body": [
                {"type": "TextBlock", "text": "PIM Access Request", "weight": "Bolder", "size": "Large"},
                {"type": "TextBlock", "text": f"User: {user_id}"},
                {"type": "TextBlock", "text": f"Resource: {resource}"},
                {"type": "TextBlock", "text": f"Justification: {justification}", "wrap": True},
                {"type": "TextBlock", "text": f"Request ID: {pim_request_id}", "size": "Small"},
            ],
            "actions": [
                {
                    "type": "Action.Submit",
                    "title": "Approve (2h)",
                    "data": {"action": "approve", "request_id": pim_request_id},
                },
                {
                    "type": "Action.Submit",
                    "title": "Reject",
                    "data": {"action": "reject", "request_id": pim_request_id},
                },
            ],
        }

        activity = {
            "type": "message",
            "from": {"id": self.bot_id},
            "conversation": {"id": self.conversation_id},
            "recipient": {"id": self.conversation_id},
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": card,
                }
            ],
        }

        url = f"{self.service_url}v3/conversations/{self.conversation_id}/activities"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=activity, headers=headers) as resp:
                response_payload = await resp.json()
                if resp.status >= 400:
                    logger.error(
                        "Failed to send Teams approval card: status=%s response=%s",
                        resp.status,
                        response_payload,
                )
                return response_payload

    async def send_alert(self, user_id: str, reason: str, risk_score: int) -> Dict[str, Any]:
        """Send a high-risk auto-block alert to the configured Teams channel."""

        channel_id = getattr(self._settings, "TEAMS_ALERT_CHANNEL_ID", "") or self.conversation_id
        if not channel_id:
            raise ValueError(
                "TEAMS_ALERT_CHANNEL_ID or TEAMS_CHANNEL_ID must be configured to send alerts"
            )

        token = await self._get_token()

        card = {
            "type": "AdaptiveCard",
            "version": "1.5",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "HIGH RISK USER BLOCKED",
                    "weight": "Bolder",
                    "color": "Attention",
                },
                {"type": "TextBlock", "text": f"User: {user_id}"},
                {"type": "TextBlock", "text": f"Risk Score: {risk_score}/100"},
                {
                    "type": "TextBlock",
                    "text": f"Reason: {reason}",
                    "wrap": True,
                },
            ],
        }

        activity = {
            "type": "message",
            "from": {"id": self.bot_id},
            "conversation": {"id": channel_id},
            "recipient": {"id": channel_id},
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": card,
                }
            ],
        }

        url = f"{self.service_url}v3/conversations/{channel_id}/activities"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=activity, headers=headers) as resp:
                response_payload = await resp.json()
                if resp.status >= 400:
                    logger.error(
                        "Failed to send Teams alert: status=%s response=%s",
                        resp.status,
                        response_payload,
                    )
                return response_payload

    async def send_investigation_card(
        self, user_id: str, reason: str, risk_score: int
    ) -> Dict[str, Any]:
        """Send an investigation task card to the configured SecOps channel."""

        channel_id = getattr(self._settings, "INVESTIGATION_CHANNEL_ID", "")
        if not channel_id:
            raise ValueError(
                "INVESTIGATION_CHANNEL_ID must be configured to send investigation cards"
            )

        token = await self._get_token()

        card = {
            "type": "AdaptiveCard",
            "version": "1.5",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "INVESTIGATE USER",
                    "weight": "Bolder",
                    "color": "Warning",
                },
                {"type": "TextBlock", "text": f"User: {user_id}"},
                {"type": "TextBlock", "text": f"Risk: {risk_score}/100"},
                {"type": "TextBlock", "text": f"Reason: {reason}", "wrap": True},
            ],
            "actions": [
                {
                    "type": "Action.Submit",
                    "title": "Re-enable User",
                    "data": {"action": "re_enable", "user_id": user_id},
                },
                {
                    "type": "Action.Submit",
                    "title": "Keep Blocked",
                    "data": {"action": "keep_blocked", "user_id": user_id},
                },
            ],
        }

        activity = {
            "type": "message",
            "conversation": {"id": channel_id},
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": card,
                }
            ],
        }

        url = f"{self.service_url}v3/conversations/{channel_id}/activities"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=activity, headers=headers) as resp:
                response_payload = await resp.json()
                if resp.status >= 400:
                    logger.error(
                        "Failed to send Teams investigation card: status=%s response=%s",
                        resp.status,
                        response_payload,
                    )
                return response_payload
