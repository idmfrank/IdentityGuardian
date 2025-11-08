import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient
from ..config.settings import settings
from ..integrations.grc import GRCProvider
from ..integrations.identity_provider import IdentityProvider, get_identity_provider
from ..integrations.itsm import ITSMProvider
from ..integrations.scim import get_scim_outbound
from ..models.identity import AccessRequest, AccessRequestStatus
from ..utils.telemetry import agent_metrics


logger = logging.getLogger(__name__)


class AccessRequestAgent:
    def __init__(
        self,
        model_client: OpenAIChatCompletionClient,
        itsm_provider: ITSMProvider,
        grc_provider: GRCProvider,
        identity_provider: Optional[IdentityProvider] = None
    ):
        self.itsm_provider = itsm_provider
        self.grc_provider = grc_provider
        self.identity_provider = identity_provider
        self.model_client = model_client
        self.pending_requests = {}
        
        system_message = """You are an Access Request Agent specialized in identity security.
        
Your responsibilities:
1. Process access requests from users
2. Validate requests against business policies and compliance requirements
3. Assess risk and identify policy violations
4. Route requests to appropriate approvers
5. Provide recommendations for approval or rejection
6. Automate provisioning once approved

When processing requests, you should:
- Check if the user exists and is active
- Evaluate the business justification
- Check for policy violations using GRC integration
- Calculate risk scores based on resource sensitivity and access level
- Identify required approvers (manager, resource owner, security team)
- Create ITSM tickets for manual provisioning when needed

Always provide clear, actionable recommendations."""

        self.agent = AssistantAgent(
            name="access_request_agent",
            model_client=model_client,
            system_message=system_message,
            description="Handles access request intake, validation, and approval workflows"
        )

    async def handle_request(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle an inbound access request and mirror membership to mapped SCIM groups."""

        required_fields = ["user_id", "resource_id", "access_level", "business_justification"]
        missing = [field for field in required_fields if not data.get(field)]
        if missing:
            raise ValueError(f"Missing required request fields: {', '.join(missing)}")

        result = await self.process_request(
            user_id=data["user_id"],
            resource_id=data["resource_id"],
            resource_type=data.get("resource_type", "application"),
            access_level=data["access_level"],
            business_justification=data["business_justification"],
        )

        role_name = data.get("resource_id")
        group_name = settings.ROLE_TO_GROUP_MAP.get(role_name) if role_name else None
        if not group_name:
            return result

        try:
            scim = get_scim_outbound()
        except ValueError as exc:
            logger.info("SCIM outbound disabled: %s", exc)
            return result

        try:
            group_id = await self.get_or_create_scim_group(group_name, scim)
        except Exception as exc:  # pragma: no cover - network failure paths
            logger.error("Failed to sync SCIM group for role %s: %s", role_name, exc, exc_info=True)
            result["group_sync"] = {
                "displayName": group_name,
                "status": "error",
                "detail": str(exc),
            }
            return result

        if group_id:
            await scim.update_group_members(group_id, add=[data["user_id"]])
            result["group_sync"] = {
                "displayName": f"{settings.SCIM_GROUP_PREFIX or ''}{group_name}",
                "groupId": group_id,
                "status": "member_added",
            }

        return result
    
    async def process_request(
        self,
        user_id: str,
        resource_id: str,
        resource_type: str,
        access_level: str,
        business_justification: str
    ) -> Dict[str, Any]:
        agent_metrics.record_event("access_request_agent", "request_received", {
            "user_id": user_id,
            "resource_id": resource_id
        })
        
        provider = await self._ensure_identity_provider()
        user = await provider.get_user(user_id)
        if not user:
            return {
                "status": "rejected",
                "reason": "User not found or inactive"
            }

        entitlements_summary = await provider.get_current_entitlements(user_id)
        
        compliance_check = await self.grc_provider.check_policy_compliance(
            user_id, resource_id, access_level
        )
        
        risk_score = self._calculate_risk_score(
            user, resource_id, access_level, compliance_check
        )
        
        request_id = str(uuid.uuid4())
        approvers = self._determine_approvers(user, resource_id, risk_score, compliance_check)
        
        access_request = AccessRequest(
            request_id=request_id,
            user_id=user_id,
            resource_id=resource_id,
            resource_type=resource_type,
            access_level=access_level,
            business_justification=business_justification,
            requested_at=datetime.now(),
            requested_by=user_id,
            approvers=approvers,
            status=AccessRequestStatus.PENDING,
            risk_score=risk_score,
            policy_violations=[v["violation"] for v in compliance_check.get("violations", [])]
        )
        
        self.pending_requests[request_id] = access_request
        
        ticket_id = await self.itsm_provider.create_ticket(
            title=f"Access Request: {user.username} -> {resource_id}",
            description=f"User {user.username} requests {access_level} access to {resource_id}.\n\nJustification: {business_justification}",
            category="Access Request",
            priority="Medium" if risk_score < 0.7 else "High"
        )
        
        recommendation = await self._get_ai_recommendation(access_request, compliance_check)
        
        agent_metrics.record_event("access_request_agent", "request_processed", {
            "request_id": request_id,
            "risk_score": risk_score,
            "violations": len(access_request.policy_violations)
        })
        
        return {
            "request_id": request_id,
            "status": "pending_approval",
            "risk_score": risk_score,
            "policy_violations": access_request.policy_violations,
            "approvers": approvers,
            "ticket_id": ticket_id,
            "recommendation": recommendation,
            "entitlements": entitlements_summary
        }
    
    def _calculate_risk_score(
        self,
        user: Any,
        resource_id: str,
        access_level: str,
        compliance_check: Dict[str, Any]
    ) -> float:
        base_score = 0.3
        
        if "admin" in access_level.lower() or "privileged" in access_level.lower():
            base_score += 0.3
        
        if not compliance_check.get("compliant", True):
            base_score += 0.2 * len(compliance_check.get("violations", []))
        
        if any(sensitive in resource_id.lower() for sensitive in ["pii", "financial", "production"]):
            base_score += 0.2
        
        return min(base_score, 1.0)
    
    def _determine_approvers(
        self,
        user: Any,
        resource_id: str,
        risk_score: float,
        compliance_check: Dict[str, Any]
    ) -> List[str]:
        approvers = []
        
        if user.manager_id:
            approvers.append(user.manager_id)
        
        if risk_score > 0.5:
            approvers.append("security_team")
        
        if any(sensitive in resource_id.lower() for sensitive in ["pii", "financial"]):
            approvers.append("data_protection_officer")
        
        if not compliance_check.get("compliant", True):
            approvers.append("compliance_team")
        
        return approvers
    
    async def _get_ai_recommendation(
        self,
        request: AccessRequest,
        compliance_check: Dict[str, Any]
    ) -> str:
        prompt = f"""Analyze this access request and provide a recommendation:

User: {request.user_id}
Resource: {request.resource_id} ({request.resource_type})
Access Level: {request.access_level}
Justification: {request.business_justification}
Risk Score: {request.risk_score}
Policy Violations: {', '.join(request.policy_violations) if request.policy_violations else 'None'}
Compliant: {compliance_check.get('compliant', True)}

Provide a brief recommendation (approve/reject/conditional) with reasoning."""

        result = await self.model_client.create([TextMessage(content=prompt, source="user")])
        return result.content if hasattr(result, 'content') else str(result)
    
    async def approve_request(self, request_id: str, approver_id: str) -> Dict[str, Any]:
        if request_id not in self.pending_requests:
            return {"success": False, "reason": "Request not found"}
        
        request = self.pending_requests[request_id]
        request.status = AccessRequestStatus.APPROVED
        request.approved_by = approver_id
        request.approved_at = datetime.now()

        provider = await self._ensure_identity_provider()
        access_response = await provider.request_access(
            request.user_id,
            request.resource_id,
            request.business_justification,
            request.access_level
        )

        provisioned = not access_response.lower().startswith("error")
        
        if provisioned:
            request.status = AccessRequestStatus.PROVISIONED
            request.provisioned_at = datetime.now()
        
        agent_metrics.record_event("access_request_agent", "request_approved", {
            "request_id": request_id,
            "approver_id": approver_id
        })
        
        return {
            "success": True,
            "request_id": request_id,
            "status": request.status.value,
            "provisioned": provisioned,
            "provisioning_message": access_response
        }

    async def get_or_create_scim_group(
        self, display_name: str, scim_client=None
    ) -> Optional[str]:
        """Return the SCIM group identifier for the supplied display name, creating it if missing."""

        scim = scim_client or get_scim_outbound()
        normalized = f"{settings.SCIM_GROUP_PREFIX or ''}{display_name}" if settings.SCIM_GROUP_PREFIX else display_name
        filter_query = f'displayName eq "{normalized}"'

        response = await scim.list_groups(filter=filter_query)
        resources: List[Any]
        if hasattr(response, "resources"):
            resources = response.resources or []
        elif isinstance(response, dict):
            resources = response.get("Resources", [])
        else:
            resources = []

        if resources:
            first = resources[0]
            if isinstance(first, dict):
                return first.get("id") or first.get("Id")
            return getattr(first, "id", None)

        created = await scim.create_group(display_name)
        if isinstance(created, dict):
            return created.get("id") or created.get("Id")
        return getattr(created, "id", None)

    async def _ensure_identity_provider(self) -> IdentityProvider:
        if self.identity_provider is None:
            self.identity_provider = await get_identity_provider()
        return self.identity_provider
