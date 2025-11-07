import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from msgraph.core import APIVersion

from ..config.settings import (
    PRIVILEGED_RESOURCE_ROLE_MAP,
    RESOURCE_GROUP_MAP,
    get_graph_client,
)
from ..integrations.teams_bot import TeamsApprovalBot
from ..models.identity import User, UserStatus

logger = logging.getLogger(__name__)


class IdentityProvider(ABC):
    @abstractmethod
    async def get_user(self, user_id: str) -> Optional[User]:
        pass

    @abstractmethod
    async def list_users(self, filters: Optional[Dict[str, Any]] = None) -> List[User]:
        pass

    @abstractmethod
    async def provision_access(self, user_id: str, resource_id: str, access_level: str) -> bool:
        pass

    @abstractmethod
    async def revoke_access(self, user_id: str, resource_id: str) -> bool:
        pass

    @abstractmethod
    async def get_user_access(self, user_id: str) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def get_user_risk(self, user_id: str) -> str:
        pass

    @abstractmethod
    async def disable_user(self, user_id: str, reason: str) -> str:
        """Disable or suspend the specified user account."""
        pass

    async def get_current_entitlements(self, user_id: str) -> str:
        """Return a human-readable summary of a user's recorded access."""
        assignments = await self.get_user_access(user_id)
        if not assignments:
            return f"No entitlements found for {user_id}."

        formatted = []
        for assignment in assignments:
            resource = assignment.get("display_name") or assignment.get("resource_id", "unknown")
            level = assignment.get("access_level", "member")
            formatted.append(f"{resource} ({level})")

        return f"Entitlements for {user_id}: " + ", ".join(formatted)

    async def request_access(
        self,
        user_id: str,
        resource: str,
        justification: str,
        access_level: Optional[Union[str, Dict[str, Any]]] = None,
    ) -> str:
        """Submit an access request and return a status message."""
        membership_level = access_level if isinstance(access_level, str) else "member"
        success = await self.provision_access(user_id, resource, membership_level or "member")
        if success:
            return (
                f"Access request submitted for {user_id} to {resource}. "
                f"Justification recorded: {justification}"
            )
        return "Error: Access request failed."

    async def deprovision_user(self, user_id: str) -> str:
        """Remove all recorded access for a user."""
        assignments = await self.get_user_access(user_id)
        success = True
        for assignment in assignments:
            resource_id = assignment.get("resource_id")
            if resource_id:
                success = success and await self.revoke_access(user_id, resource_id)

        if success:
            return f"User {user_id} deprovisioned from recorded resources."
        return "Error: Failed to deprovision one or more resources."


class MockIdentityProvider(IdentityProvider):
    def __init__(self):
        self.users = self._create_mock_users()
        self.access_assignments: Dict[str, List[Dict[str, Any]]] = {}

    def _create_mock_users(self) -> Dict[str, User]:
        return {
            "user001": User(
                user_id="user001",
                username="john.doe",
                email="john.doe@company.com",
                first_name="John",
                last_name="Doe",
                department="Engineering",
                manager_id="mgr001",
                status=UserStatus.ACTIVE,
                hire_date=datetime(2022, 1, 15),
                roles=["Developer", "Team Lead"],
            ),
            "user002": User(
                user_id="user002",
                username="jane.smith",
                email="jane.smith@company.com",
                first_name="Jane",
                last_name="Smith",
                department="Finance",
                manager_id="mgr002",
                status=UserStatus.ACTIVE,
                hire_date=datetime(2021, 6, 1),
                roles=["Financial Analyst"],
            ),
            "user003": User(
                user_id="user003",
                username="bob.wilson",
                email="bob.wilson@company.com",
                first_name="Bob",
                last_name="Wilson",
                department="Security",
                manager_id="mgr003",
                status=UserStatus.ACTIVE,
                hire_date=datetime(2020, 3, 10),
                roles=["Security Analyst", "SIEM Admin"],
            ),
        }

    async def get_user(self, user_id: str) -> Optional[User]:
        return self.users.get(user_id)

    async def list_users(self, filters: Optional[Dict[str, Any]] = None) -> List[User]:
        users = list(self.users.values())
        if filters:
            if "department" in filters:
                users = [u for u in users if u.department == filters["department"]]
            if "status" in filters:
                target_status = filters["status"]
                if isinstance(target_status, str):
                    try:
                        target_status = UserStatus(target_status)
                    except ValueError:
                        target_status = None
                if target_status:
                    users = [u for u in users if u.status == target_status]
        return users

    async def provision_access(self, user_id: str, resource_id: str, access_level: str) -> bool:
        if user_id not in self.users:
            return False

        if user_id not in self.access_assignments:
            self.access_assignments[user_id] = []

        self.access_assignments[user_id].append(
            {
                "resource_id": resource_id,
                "access_level": access_level,
                "granted_at": datetime.now(),
            }
        )
        return True

    async def revoke_access(self, user_id: str, resource_id: str) -> bool:
        if user_id not in self.access_assignments:
            return False

        self.access_assignments[user_id] = [
            a for a in self.access_assignments[user_id] if a["resource_id"] != resource_id
        ]
        return True

    async def get_user_access(self, user_id: str) -> List[Dict[str, Any]]:
        return self.access_assignments.get(user_id, [])

    async def get_current_entitlements(self, user_id: str) -> str:
        assignments = await self.get_user_access(user_id)
        if not assignments:
            return f"Mock entitlements for {user_id}: none recorded."

        formatted = [
            f"{assignment['resource_id']} ({assignment.get('access_level', 'member')})"
            for assignment in assignments
        ]
        return f"Mock entitlements for {user_id}: " + ", ".join(formatted)

    async def get_user_risk(self, user_id: str) -> str:
        return "Identity Protection Risk: none (mock)"

    async def disable_user(self, user_id: str, reason: str) -> str:
        user = self.users.get(user_id)
        if not user:
            return "Error: User not found"

        user.status = UserStatus.SUSPENDED
        return f"User {user_id} disabled. Reason: {reason}"

    async def request_access(
        self,
        user_id: str,
        resource: str,
        justification: str,
        access_level: Optional[Union[str, Dict[str, Any]]] = None,
    ) -> str:
        membership_level = access_level if isinstance(access_level, str) else "member"
        success = await self.provision_access(user_id, resource, membership_level or "member")
        if success:
            assignments = self.access_assignments.get(user_id, [])
            if assignments:
                assignments[-1]["justification"] = justification
            return (
                f"Access request submitted for {user_id} to {resource}. "
                "JIT activation link sent (mock)."
            )
        return "Error: Access request failed."

    async def deprovision_user(self, user_id: str) -> str:
        if user_id in self.users:
            self.users[user_id].status = UserStatus.INACTIVE
        self.access_assignments.pop(user_id, None)
        return (
            f"User {user_id} deprovisioned across mock Entra ID, Okta, and HR systems."
        )


class AzureIdentityProvider(IdentityProvider):
    def __init__(self) -> None:
        self._logger = logging.getLogger(f"{__name__}.AzureIdentityProvider")

    def _format_datetime_for_graph(self, value: Union[str, datetime]) -> str:
        """Return an ISO 8601 UTC timestamp suitable for Graph requests."""
        if isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            else:
                value = value.astimezone(timezone.utc)
            normalized = value.replace(microsecond=0)
        elif isinstance(value, str):
            candidate = value.strip()
            if not candidate:
                raise ValueError("startDateTime cannot be empty")
            if candidate.endswith("Z"):
                candidate = candidate[:-1] + "+00:00"
            try:
                parsed = datetime.fromisoformat(candidate)
            except ValueError as exc:
                raise ValueError("Invalid ISO 8601 date string for startDateTime") from exc
            normalized = parsed.astimezone(timezone.utc).replace(microsecond=0)
        else:
            raise ValueError("startDateTime must be a datetime or ISO 8601 string")

        return normalized.isoformat().replace("+00:00", "Z")

    def _build_privileged_role_request_body(
        self,
        user_id: str,
        justification: str,
        role_config: Dict[str, Any],
        schedule_overrides: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        role_definition_id = role_config.get("role_definition_id")
        if not role_definition_id:
            raise ValueError("Privileged role configuration is missing 'role_definition_id'")

        directory_scope_id = role_config.get("directory_scope_id", "/")
        base_schedule = role_config.get("schedule_info", {})
        schedule_overrides = schedule_overrides or {}

        schedule_info: Dict[str, Any] = {**base_schedule, **schedule_overrides}

        start_value: Union[str, datetime]
        if "startDateTime" in schedule_info:
            start_value = schedule_info["startDateTime"]
        else:
            start_value = datetime.now(timezone.utc).replace(microsecond=0)

        start_time = self._format_datetime_for_graph(start_value)

        expiration = schedule_info.get("expiration")
        if not isinstance(expiration, dict):
            duration = role_config.get("duration", "PT2H")
            expiration = {"type": "afterDuration", "duration": duration}

        schedule_payload = {
            "startDateTime": start_time,
            "expiration": expiration,
        }

        return {
            "principalId": user_id,
            "roleDefinitionId": role_definition_id,
            "directoryScopeId": directory_scope_id,
            "justification": justification,
            "scheduleInfo": schedule_payload,
        }

    async def _get_client(self):
        client = await get_graph_client()
        if client is None:
            raise ValueError("Graph client not initialized")
        return client

    async def get_user(self, user_id: str) -> Optional[User]:
        client = await self._get_client()
        try:
            graph_user = await client.users.by_user_id(user_id).get()
        except Exception as exc:
            self._logger.error("Error fetching user %s: %s", user_id, exc, exc_info=True)
            return None

        data = self._to_dict(graph_user)
        if not data:
            return None

        try:
            manager_id = await self._get_manager_id(client, data.get("id"))
        except Exception:
            manager_id = None

        user = self._map_user_dict(data, manager_id=manager_id)
        return user

    async def list_users(self, filters: Optional[Dict[str, Any]] = None) -> List[User]:
        client = await self._get_client()
        try:
            response = await client.users.get()
        except Exception as exc:
            self._logger.error("Error listing users: %s", exc, exc_info=True)
            return []

        users: List[User] = []
        for item in getattr(response, "value", []):
            data = self._to_dict(item)
            if not data:
                continue
            user = self._map_user_dict(data)
            if not user.user_id:
                continue

            if filters:
                if "department" in filters and user.department != filters["department"]:
                    continue
                if "status" in filters:
                    target_status = filters["status"]
                    if isinstance(target_status, str):
                        try:
                            target_status = UserStatus(target_status)
                        except ValueError:
                            target_status = None
                    if target_status and user.status != target_status:
                        continue
            users.append(user)

        return users

    async def provision_access(self, user_id: str, resource_id: str, access_level: str) -> bool:
        client = await self._get_client()
        membership_body = {
            "@odata.id": f"https://graph.microsoft.com/v1.0/directoryObjects/{user_id}"
        }
        try:
            await client.groups.by_group_id(resource_id).members.ref.post(membership_body)
            self._logger.info(
                "Granted %s membership in group %s with level %s",
                user_id,
                resource_id,
                access_level,
            )
            return True
        except Exception as exc:
            self._logger.error(
                "Error provisioning access for %s to %s: %s", user_id, resource_id, exc, exc_info=True
            )
            return False

    async def revoke_access(self, user_id: str, resource_id: str) -> bool:
        client = await self._get_client()
        try:
            await client.groups.by_group_id(resource_id).members.by_directory_object_id(user_id).ref.delete()
            self._logger.info("Removed %s from group %s", user_id, resource_id)
            return True
        except Exception as exc:
            self._logger.error(
                "Error revoking access for %s from %s: %s", user_id, resource_id, exc, exc_info=True
            )
            return False

    async def get_user_access(self, user_id: str) -> List[Dict[str, Any]]:
        client = await self._get_client()
        assignments: List[Dict[str, Any]] = []

        try:
            member_of = await client.users.by_user_id(user_id).member_of.get()
            for item in getattr(member_of, "value", []):
                data = self._to_dict(item)
                if not data:
                    continue
                odata_type = (data.get("@odata.type") or data.get("odata_type") or "").lower()
                display_name = data.get("display_name") or data.get("displayName")
                resource_id = data.get("id") or display_name or "group"

                if "group" in odata_type:
                    assignments.append(
                        {
                            "resource_id": resource_id,
                            "resource_type": "group",
                            "display_name": display_name or resource_id,
                            "access_level": "member",
                            "granted_at": datetime.now(),
                        }
                    )
                elif "directoryrole" in odata_type:
                    assignments.append(
                        {
                            "resource_id": resource_id,
                            "resource_type": "role",
                            "display_name": display_name or resource_id,
                            "access_level": "eligible"
                            if "eligible" in (display_name or "").lower()
                            else "active",
                            "granted_at": datetime.now(),
                        }
                    )
        except Exception as exc:
            self._logger.error("Error fetching group/role assignments: %s", exc, exc_info=True)

        try:
            app_roles = await client.users.by_user_id(user_id).app_role_assignments.get()
            for assignment in getattr(app_roles, "value", []):
                data = self._to_dict(assignment)
                if not data:
                    continue
                assignments.append(
                    {
                        "resource_id": data.get("app_display_name")
                        or data.get("resource_display_name")
                        or data.get("resource_id")
                        or "application",
                        "resource_type": "application",
                        "display_name": data.get("display_name")
                        or data.get("app_display_name")
                        or data.get("resource_display_name"),
                        "access_level": data.get("principal_type") or "appRole",
                        "granted_at": self._parse_datetime(
                            data.get("created_date_time") or data.get("createdDateTime")
                        )
                        or datetime.now(),
                    }
                )
        except Exception as exc:
            self._logger.error("Error fetching app role assignments: %s", exc, exc_info=True)

        return assignments

    async def disable_user(self, user_id: str, reason: str) -> str:
        client = await self._get_client()
        payload = {"accountEnabled": False}

        try:
            await client.users.by_user_id(user_id).patch(payload)
        except Exception as exc:
            self._logger.error("Failed to disable %s: %s", user_id, exc, exc_info=True)
            return f"Error disabling user: {exc}"

        self._logger.info("User %s disabled via Graph API. Reason: %s", user_id, reason)
        return f"User {user_id} disabled. Reason: {reason}"

    async def get_current_entitlements(self, user_id: str) -> str:
        assignments = await self.get_user_access(user_id)
        if not assignments:
            return f"No entitlements found for {user_id}."

        groups = [a for a in assignments if a.get("resource_type") == "group"]
        roles = [a for a in assignments if a.get("resource_type") == "role"]
        apps = [a for a in assignments if a.get("resource_type") == "application"]

        def _join(items: List[Dict[str, Any]]) -> str:
            return ", ".join(
                item.get("display_name") or item.get("resource_id", "unknown") for item in items
            ) or "None"

        return (
            f"Entitlements for {user_id}:\n"
            f"Groups: {_join(groups)}\n"
            f"Roles: {_join(roles)}\n"
            f"Apps: {_join(apps)}"
        )

    async def request_access(
        self,
        user_id: str,
        resource: str,
        justification: str,
        access_level: Optional[Union[str, Dict[str, Any]]] = None,
    ) -> str:
        self._logger.info(
            "Submitting access request for user %s to resource %s with justification '%s'",
            user_id,
            resource,
            justification,
        )
        client = await self._get_client()
        normalized_resource = resource.lower().replace(" ", "_")
        privileged_role = PRIVILEGED_RESOURCE_ROLE_MAP.get(normalized_resource)
        if privileged_role:
            schedule_overrides = None
            if isinstance(access_level, dict):
                # Allow callers to pass schedule overrides as part of the access_level payload.
                schedule_overrides = access_level.get("schedule") if "schedule" in access_level else access_level

            try:
                body = self._build_privileged_role_request_body(
                    user_id,
                    justification,
                    privileged_role,
                    schedule_overrides=schedule_overrides,
                )
            except ValueError as exc:
                self._logger.error(
                    "Invalid privileged access configuration for resource %s: %s",
                    resource,
                    exc,
                    exc_info=True,
                )
                return f"Error: {exc}"

            try:
                response = await client.identity_governance.privileged_access.role_assignment_requests.post(
                    body,
                    api_version=APIVersion.BETA,
                )
                request_payload = self._to_dict(response) if response else {}
                request_id = request_payload.get("id") or request_payload.get("request_id")

                if request_id:
                    try:
                        bot = TeamsApprovalBot()
                        await bot.send_approval_card(user_id, resource, justification, request_id)
                        return (
                            f"PIM request {request_id} sent to Teams for approval."
                        )
                    except Exception as exc:
                        self._logger.warning(
                            "Privileged request %s created but Teams notification failed: %s",
                            request_id,
                            exc,
                            exc_info=True,
                        )
                        return (
                            f"Privileged access request submitted for {user_id} to {resource}. "
                            "Teams notification failed; approval required in PIM portal."
                        )

                return (
                    f"Privileged access request submitted for {user_id} to {resource}. "
                    "Justification recorded and pending PIM approval."
                )
            except Exception as exc:
                self._logger.error(
                    "Error submitting privileged access request for %s to %s: %s",
                    user_id,
                    resource,
                    exc,
                    exc_info=True,
                )
                return (
                    "Error: Privileged access request failed. Ensure the application has "
                    "PrivilegedAccess.ReadWrite.AzureAD consent and the request configuration is valid."
                )

        group_id = RESOURCE_GROUP_MAP.get(normalized_resource)
        if not group_id:
            self._logger.error("Unknown resource '%s' for access request", resource)
            return f"Error: Unknown resource '{resource}'"

        success = await self.provision_access(user_id, group_id, access_level or "member")
        if success:
            return (
                f"Access granted for {user_id} to {resource} (group {group_id}). "
                f"Justification logged: {justification}."
            )
        return "Error: Access request failed."

    async def deprovision_user(self, user_id: str) -> str:
        client = await self._get_client()
        try:
            await client.users.by_user_id(user_id).patch({"accountEnabled": False})
        except Exception as exc:
            self._logger.error("Error disabling user %s: %s", user_id, exc, exc_info=True)
            return "Error: Deprovisioning failed."

        try:
            request = client.users.by_user_id(user_id).transitive_member_of
            # Limit the selected fields to avoid Graph returning 400 errors for tenants
            # where the default projection is not allowed on transitive member requests.
            request.query_parameters_select = "id,displayName,@odata.type"
            memberships = await request.get()
            for member in getattr(memberships, "value", []):
                data = self._to_dict(member)
                if not data:
                    continue
                odata_type = (data.get("@odata.type") or data.get("odata_type") or "").lower()
                if "group" not in odata_type:
                    continue
                group_id = data.get("id")
                if not group_id:
                    continue
                try:
                    await client.groups.by_group_id(group_id).members.by_directory_object_id(user_id).ref.delete()
                except Exception as exc:
                    self._logger.warning(
                        "Failed to remove %s from group %s during deprovision: %s",
                        user_id,
                        group_id,
                        exc,
                    )
        except Exception as exc:
            self._logger.error("Error cleaning memberships for %s: %s", user_id, exc, exc_info=True)
            return "Error: Deprovisioning failed."

        return f"User {user_id} disabled and memberships removed."

    async def get_user_risk(self, user_id: str) -> str:
        client = await self._get_client()
        try:
            request = client.identity_protection.risky_users.by_risky_user_id(user_id)
            # Request only the fields we need to avoid tenants that reject the
            # broader default projection on risky user lookups.
            request.query_parameters_select = "id,riskLevel,riskState"
            risk = await request.get()
            if risk is None:
                return "Identity Protection Risk: none"

            level = getattr(risk, "risk_level", None) or getattr(risk, "riskLevel", None)
            if not level:
                risk_dict = self._to_dict(risk)
                level = risk_dict.get("risk_level") or risk_dict.get("riskLevel")

            level_str = str(level).lower() if level else "none"
            return f"Identity Protection Risk: {level_str}"
        except Exception as exc:
            self._logger.debug(
                "Identity Protection risk lookup failed for %s: %s", user_id, exc, exc_info=True
            )
            return "Identity Protection: Not available"

    async def _get_manager_id(self, client, user_object_id: Optional[str]) -> Optional[str]:
        if not user_object_id:
            return None
        try:
            manager = await client.users.by_user_id(user_object_id).manager.get()
            manager_dict = self._to_dict(manager)
            return manager_dict.get("id")
        except Exception as exc:
            self._logger.debug("No manager found for %s: %s", user_object_id, exc)
            return None

    def _map_user_dict(self, data: Dict[str, Any], manager_id: Optional[str] = None) -> User:
        hire_date = self._parse_datetime(
            data.get("employee_hire_date") or data.get("employeeHireDate")
        ) or datetime.now()
        account_enabled = data.get("account_enabled")
        if account_enabled is None:
            account_enabled = data.get("accountEnabled", True)

        status = UserStatus.ACTIVE if account_enabled else UserStatus.SUSPENDED
        attributes = {}
        for key in [
            "jobTitle",
            "officeLocation",
            "mobilePhone",
            "userType",
        ]:
            value = data.get(key)
            if value:
                attributes[key] = value

        return User(
            user_id=data.get("id") or data.get("user_id") or data.get("userPrincipalName") or "",
            username=data.get("user_principal_name")
            or data.get("userPrincipalName")
            or data.get("mail")
            or data.get("id")
            or "",
            email=data.get("mail")
            or data.get("user_principal_name")
            or data.get("userPrincipalName")
            or "",
            first_name=data.get("given_name") or data.get("givenName") or "",
            last_name=data.get("surname") or data.get("surName") or "",
            department=data.get("department") or "Unknown",
            manager_id=manager_id or data.get("manager_id") or data.get("managerId"),
            status=status,
            hire_date=hire_date,
            roles=[],
            attributes=attributes,
        )

    def _parse_datetime(self, value: Any) -> Optional[datetime]:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str) and value:
            candidate = value
            if candidate.endswith("Z"):
                candidate = candidate[:-1] + "+00:00"
            try:
                return datetime.fromisoformat(candidate)
            except ValueError:
                return None
        return None

    def _to_dict(self, graph_object: Any) -> Dict[str, Any]:
        if graph_object is None:
            return {}
        if isinstance(graph_object, dict):
            return graph_object
        for method_name in ("model_dump", "to_dict", "as_dict"):
            method = getattr(graph_object, method_name, None)
            if callable(method):
                try:
                    return method()
                except Exception:
                    continue
        result: Dict[str, Any] = {}
        for attribute in dir(graph_object):
            if attribute.startswith("_"):
                continue
            value = getattr(graph_object, attribute)
            if callable(value):
                continue
            result[attribute] = value
        additional_data = getattr(graph_object, "additional_data", None)
        if isinstance(additional_data, dict):
            result.update(additional_data)
        return result


_provider_instance: Optional[IdentityProvider] = None


async def get_identity_provider(force_refresh: bool = False) -> IdentityProvider:
    """Return the configured identity provider instance."""
    global _provider_instance

    if not force_refresh and _provider_instance is not None:
        return _provider_instance

    provider_type = os.getenv("IDENTITY_PROVIDER", "mock").lower()
    if provider_type == "azure":
        _provider_instance = AzureIdentityProvider()
        logger.info("Using Azure identity provider integration")
    else:
        _provider_instance = MockIdentityProvider()
        if provider_type != "mock":
            logger.warning("Unknown IDENTITY_PROVIDER '%s'; defaulting to mock", provider_type)
        else:
            logger.info("Using mock identity provider integration")

    return _provider_instance
