"""SCIM 2.0 integrations for outbound provisioning and inbound server support."""
import asyncio
import logging
from typing import Any, Dict, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from scim2_client import Client as SCIMClient
from scim2_models import Group as SCIMGroup
from scim2_models import User as SCIMUser

from ..config.settings import settings
from ..models.identity import UserStatus
from .identity_provider import get_identity_provider

logger = logging.getLogger(__name__)
security = HTTPBearer()


class SCIMOutboundClient:
    """Outbound SCIM client used to push lifecycle updates to external targets."""

    def __init__(self) -> None:
        if not settings.SCIM_TARGET_BASE_URL or not settings.SCIM_TARGET_BEARER_TOKEN:
            raise ValueError(
                "SCIM_TARGET_BASE_URL and SCIM_TARGET_BEARER_TOKEN are required for outbound SCIM operations."
            )

        self.client = SCIMClient(
            settings.SCIM_TARGET_BASE_URL,
            bearer_token=settings.SCIM_TARGET_BEARER_TOKEN,
        )

    async def _execute(self, func, *args, **kwargs):
        return await asyncio.to_thread(func, *args, **kwargs)

    async def provision_user(self, user_data: Dict[str, Any]) -> str:
        """Create a new user on the SCIM target."""

        user = SCIMUser(
            userName=user_data["userPrincipalName"],
            name={
                "givenName": user_data.get("givenName", ""),
                "familyName": user_data.get("surname", ""),
            },
            active=user_data.get("active", True),
            emails=[
                {
                    "value": user_data["userPrincipalName"],
                    "primary": True,
                    "type": "work",
                }
            ],
        )

        result = await self._execute(self.client.create_user, user)
        return f"User provisioned in target: {getattr(result, 'id', 'unknown')}"

    async def update_user(self, user_id: str, user_data: Dict[str, Any]) -> str:
        """Update an existing user on the SCIM target."""

        user = SCIMUser(
            schemas=["urn:ietf:params:scim:schemas:core:2.0:User"],
            userName=user_data.get("userPrincipalName", user_id),
            active=user_data.get("active", True),
        )

        await self._execute(self.client.update_user, user_id, user)
        return f"User {user_id} updated in target."

    async def deprovision_user(self, user_id: str) -> str:
        """Deactivate a user account on the SCIM target."""

        patch = [{"op": "replace", "path": "active", "value": False}]
        await self._execute(self.client.patch_user, user_id, patch)
        return f"User {user_id} deprovisioned in target."


class SCIMInboundRequest(BaseModel):
    """Generic SCIM inbound payload for PATCH operations."""

    schemas: list[str]
    operations: Optional[list[Dict[str, Any]]] = None


class SCIMInboundServer:
    """Lightweight FastAPI application that exposes SCIM user and group endpoints."""

    def __init__(self) -> None:
        self.app = FastAPI(title="IdentityGuardian SCIM Server")
        self._provider = None
        self._setup_routes()

    async def _get_provider(self):
        if self._provider is None:
            self._provider = await get_identity_provider()
        return self._provider

    def _verify_bearer(self, credentials: HTTPAuthorizationCredentials) -> None:
        if credentials.credentials != settings.SCIM_TARGET_BEARER_TOKEN:
            logger.warning("SCIM inbound request rejected due to invalid bearer token")
            raise HTTPException(status_code=401, detail="Unauthorized")

    def _setup_routes(self) -> None:
        @self.app.get("/scim/v2/Users")
        async def list_users(credentials: HTTPAuthorizationCredentials = Depends(security)):
            self._verify_bearer(credentials)
            provider = await self._get_provider()
            users = await provider.list_users()

            resources = []
            for user in users:
                resources.append(
                    {
                        "id": getattr(user, "user_id", getattr(user, "email", "")),
                        "userName": getattr(user, "email", getattr(user, "username", "")),
                        "active": getattr(user, "status", None) == UserStatus.ACTIVE,
                        "name": {
                            "givenName": getattr(user, "first_name", ""),
                            "familyName": getattr(user, "last_name", ""),
                        },
                        "emails": [
                            {
                                "value": getattr(user, "email", ""),
                                "type": "work",
                                "primary": True,
                            }
                        ],
                    }
                )

            return {
                "Resources": resources,
                "totalResults": len(resources),
                "itemsPerPage": len(resources),
                "startIndex": 1,
            }

        @self.app.post("/scim/v2/Users")
        async def create_user(
            user: SCIMUser, credentials: HTTPAuthorizationCredentials = Depends(security)
        ):
            self._verify_bearer(credentials)
            provider = await self._get_provider()

            user_name = getattr(user, "userName", None)
            if not user_name:
                raise HTTPException(status_code=400, detail="userName is required")

            await provider.request_access(
                user_name,
                "scim_inbound_provision",
                "Inbound SCIM create",
            )

            return {"id": getattr(user, "id", user_name), "externalId": getattr(user, "external_id", None)}

        @self.app.patch("/scim/v2/Users/{user_id}")
        async def patch_user(
            user_id: str,
            request: SCIMInboundRequest,
            credentials: HTTPAuthorizationCredentials = Depends(security),
        ):
            self._verify_bearer(credentials)
            provider = await self._get_provider()

            for operation in request.operations or []:
                path = operation.get("path")
                value = operation.get("value")
                if path == "active" and value is False:
                    await provider.deprovision_user(user_id)
                    return {"status": "deprovisioned"}

            return {"status": "updated"}

        @self.app.post("/scim/v2/Groups")
        async def create_group(
            group: SCIMGroup, credentials: HTTPAuthorizationCredentials = Depends(security)
        ):
            self._verify_bearer(credentials)
            # Extend with identity provider integration as needed.
            return {"id": getattr(group, "id", None) or getattr(group, "displayName", "group")}

    def run(self) -> None:
        import uvicorn

        uvicorn.run(self.app, host=settings.SCIM_SERVER_HOST, port=settings.SCIM_SERVER_PORT)


def get_scim_outbound() -> SCIMOutboundClient:
    """Factory helper for obtaining an outbound SCIM client."""

    return SCIMOutboundClient()


def get_scim_inbound() -> SCIMInboundServer:
    """Factory helper for spinning up the inbound SCIM FastAPI server."""

    return SCIMInboundServer()


__all__ = ["SCIMOutboundClient", "SCIMInboundServer", "get_scim_outbound", "get_scim_inbound"]

