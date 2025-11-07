"""SCIM 2.0 integrations for outbound provisioning and inbound server support."""
import asyncio
import logging
import re
from typing import Any, Dict, List, Optional

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

    async def list_groups(self, filter: Optional[str] = None):
        """Return groups from the SCIM target, optionally filtered by display name."""

        kwargs: Dict[str, Any] = {}
        if filter:
            kwargs["filter"] = filter
        return await self._execute(self.client.list_groups, **kwargs)

    async def create_group(self, display_name: str, members: Optional[List[str]] = None):
        """Create a new SCIM group with an optional member list."""

        prefix = settings.SCIM_GROUP_PREFIX or ""
        group = SCIMGroup(
            displayName=f"{prefix}{display_name}",
            members=[{"value": member} for member in members] if members else [],
        )
        return await self._execute(self.client.create_group, group)

    async def update_group_members(
        self,
        group_id: str,
        add: Optional[List[str]] = None,
        remove: Optional[List[str]] = None,
    ) -> str:
        """Apply SCIM PATCH operations to add or remove group members."""

        operations: List[Dict[str, Any]] = []
        if add:
            operations.append(
                {
                    "op": "add",
                    "path": "members",
                    "value": [{"value": member} for member in add],
                }
            )
        if remove:
            for member in remove:
                operations.append(
                    {
                        "op": "remove",
                        "path": f'members[value eq "{member}"]',
                    }
                )

        if not operations:
            return f"No updates applied to group {group_id}."

        await self._execute(self.client.patch_group, group_id, operations)
        return f"Group {group_id} updated."

    async def delete_group(self, group_id: str) -> str:
        """Delete a SCIM group from the target system."""

        await self._execute(self.client.delete_group, group_id)
        return f"Group {group_id} deleted."


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

        @self.app.get("/scim/v2/Groups")
        async def list_groups(credentials: HTTPAuthorizationCredentials = Depends(security)):
            self._verify_bearer(credentials)
            provider = await self._get_provider()

            groups: List[Dict[str, Any]] = []
            list_method = getattr(provider, "list_entra_groups", None)
            if callable(list_method):
                try:
                    entra_groups = await list_method(settings.SCIM_GROUP_PREFIX or None)
                    for group in entra_groups:
                        display_name = group.get("displayName") or group.get("display_name")
                        groups.append({"id": group.get("id"), "displayName": display_name})
                except Exception as exc:  # pragma: no cover - provider failures
                    logger.error("Failed to list provider groups: %s", exc, exc_info=True)

            if not groups:
                fallback_name = f"{settings.SCIM_GROUP_PREFIX or ''}Sample-Group"
                groups = [{"id": "sample-group", "displayName": fallback_name}]

            return {
                "Resources": groups,
                "totalResults": len(groups),
                "itemsPerPage": len(groups),
                "startIndex": 1,
            }

        @self.app.post("/scim/v2/Groups")
        async def create_group(
            group: SCIMGroup, credentials: HTTPAuthorizationCredentials = Depends(security)
        ):
            self._verify_bearer(credentials)

            provider = await self._get_provider()
            display_name = getattr(group, "display_name", None) or getattr(group, "displayName", None)
            if not display_name:
                raise HTTPException(status_code=400, detail="displayName is required")

            create_method = getattr(provider, "create_entra_group", None)
            if callable(create_method):
                entra_group = await create_method(display_name)
                entra_dict = getattr(entra_group, "model_dump", None)
                if callable(entra_dict):
                    entra_group = entra_dict()
                if isinstance(entra_group, dict):
                    group_id = entra_group.get("id") or entra_group.get("group_id")
                else:
                    group_id = getattr(entra_group, "id", display_name)
                return {"id": group_id, "displayName": display_name}

            return {"id": display_name, "displayName": display_name}

        @self.app.patch("/scim/v2/Groups/{group_id}")
        async def patch_group(
            group_id: str,
            request: SCIMInboundRequest,
            credentials: HTTPAuthorizationCredentials = Depends(security),
        ):
            self._verify_bearer(credentials)
            provider = await self._get_provider()

            add_method = getattr(provider, "add_users_to_group", None)
            remove_method = getattr(provider, "remove_users_from_group", None)

            for operation in request.operations or []:
                op = (operation.get("op") or "").lower()
                if op == "add":
                    value = operation.get("value", [])
                    if isinstance(value, dict):
                        value = [value]
                    members = [item.get("value") for item in value if item.get("value")]
                    if members:
                        if callable(add_method):
                            await add_method(group_id, members)
                        else:
                            for member in members:
                                await provider.provision_access(member, group_id, "member")
                elif op == "remove":
                    member = self._extract_member_from_path(operation.get("path"))
                    if not member:
                        raw_value = operation.get("value") or []
                        if isinstance(raw_value, dict):
                            raw_value = [raw_value]
                        if isinstance(raw_value, list) and raw_value:
                            member = raw_value[0].get("value")
                    if member:
                        if callable(remove_method):
                            await remove_method(group_id, [member])
                        else:
                            await provider.revoke_access(member, group_id)

            return {"status": "updated"}

        @self.app.delete("/scim/v2/Groups/{group_id}")
        async def delete_group(
            group_id: str, credentials: HTTPAuthorizationCredentials = Depends(security)
        ):
            self._verify_bearer(credentials)
            provider = await self._get_provider()

            delete_method = getattr(provider, "delete_entra_group", None)
            if callable(delete_method):
                await delete_method(group_id)

            return {"status": "deleted"}

    @staticmethod
    def _extract_member_from_path(path: Optional[str]) -> Optional[str]:
        if not path:
            return None
        match = re.search(r'members\[value eq "([^"]+)"\]', path)
        if match:
            return match.group(1)
        return None

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

