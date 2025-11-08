from typing import Dict, Any, List
from datetime import datetime, timedelta
import uuid
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient
from ..models.identity import ReviewCampaign, AccessReviewItem, ReviewStatus
from ..integrations.identity_provider import IdentityProvider
from ..integrations.grc import GRCProvider
from ..utils.telemetry import agent_metrics


class AccessReviewAgent:
    def __init__(
        self,
        model_client: OpenAIChatCompletionClient,
        identity_provider: IdentityProvider,
        grc_provider: GRCProvider
    ):
        self.identity_provider = identity_provider
        self.grc_provider = grc_provider
        self.campaigns = {}
        self.model_client = model_client
        
        system_message = """You are an Access Review Agent specialized in identity governance.

Your responsibilities:
1. Generate periodic access review campaigns
2. Analyze user access patterns and usage
3. Provide intelligent recommendations for access certification
4. Identify unused, excessive, or risky access
5. Automate revocation of inappropriate access
6. Ensure compliance with review requirements

When reviewing access, consider:
- Last usage date and access frequency
- Business need and role appropriateness
- Policy compliance and risk indicators
- Segregation of duties violations
- Orphaned or dormant accounts

Provide clear, risk-based recommendations for each access item."""

        self.agent = AssistantAgent(
            name="access_review_agent",
            model_client=model_client,
            system_message=system_message,
            description="Automates periodic access reviews and provides intelligent recommendations"
        )
    
    async def create_campaign(
        self,
        campaign_name: str,
        scope: str,
        duration_days: int = 30,
        created_by: str = "system"
    ) -> Dict[str, Any]:
        agent_metrics.record_event("access_review_agent", "campaign_created", {
            "campaign_name": campaign_name,
            "scope": scope
        })
        
        campaign_id = str(uuid.uuid4())
        users = await self.identity_provider.list_users()
        
        review_items = []
        for user in users:
            user_access = await self.identity_provider.get_user_access(user.user_id)
            
            for access in user_access:
                review_item = await self._create_review_item(
                    campaign_id, user.user_id, access, user.manager_id or "default_reviewer"
                )
                review_items.append(review_item)
        
        campaign = ReviewCampaign(
            campaign_id=campaign_id,
            campaign_name=campaign_name,
            scope=scope,
            created_at=datetime.now(),
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=duration_days),
            created_by=created_by,
            review_items=review_items,
            status="active"
        )
        
        self.campaigns[campaign_id] = campaign
        
        agent_metrics.record_event("access_review_agent", "campaign_items_generated", {
            "campaign_id": campaign_id,
            "item_count": len(review_items)
        })
        
        return {
            "campaign_id": campaign_id,
            "campaign_name": campaign_name,
            "review_items_count": len(review_items),
            "start_date": campaign.start_date,
            "end_date": campaign.end_date
        }
    
    async def _create_review_item(
        self,
        campaign_id: str,
        user_id: str,
        access: Dict[str, Any],
        reviewer_id: str
    ) -> AccessReviewItem:
        resource_id = access.get("resource_id", "unknown")
        access_level = access.get("access_level", "unknown")
        granted_at = access.get("granted_at", datetime.now())
        
        compliance_check = await self.grc_provider.check_policy_compliance(
            user_id, resource_id, access_level
        )
        
        risk_score = 0.3
        if not compliance_check.get("compliant", True):
            risk_score += 0.3
        
        days_since_grant = (datetime.now() - granted_at).days
        if days_since_grant > 180:
            risk_score += 0.2
        
        recommendation = await self._get_ai_recommendation(
            user_id, resource_id, access_level, risk_score, compliance_check
        )
        
        return AccessReviewItem(
            review_item_id=str(uuid.uuid4()),
            campaign_id=campaign_id,
            user_id=user_id,
            resource_id=resource_id,
            resource_type="application",
            access_level=access_level,
            last_used=granted_at,
            assigned_date=granted_at,
            reviewer_id=reviewer_id,
            status=ReviewStatus.PENDING,
            recommendation=recommendation,
            risk_score=min(risk_score, 1.0)
        )
    
    async def _get_ai_recommendation(
        self,
        user_id: str,
        resource_id: str,
        access_level: str,
        risk_score: float,
        compliance_check: Dict[str, Any]
    ) -> str:
        prompt = f"""Review this access and recommend action:

User: {user_id}
Resource: {resource_id}
Access Level: {access_level}
Risk Score: {risk_score:.2f}
Compliant: {compliance_check.get('compliant', True)}
Violations: {', '.join([v['violation'] for v in compliance_check.get('violations', [])])}

Provide a one-word recommendation: APPROVE, REVOKE, or MODIFY."""

        result = await self.model_client.create([TextMessage(content=prompt, source="user")])
        content = result.content if hasattr(result, 'content') else str(result)
        
        if "REVOKE" in content.upper():
            return "REVOKE"
        elif "MODIFY" in content.upper():
            return "MODIFY"
        else:
            return "APPROVE"
    
    async def process_review_decision(
        self,
        campaign_id: str,
        review_item_id: str,
        decision: str,
        reviewer_id: str,
        justification: str = ""
    ) -> Dict[str, Any]:
        if campaign_id not in self.campaigns:
            return {"success": False, "reason": "Campaign not found"}
        
        campaign = self.campaigns[campaign_id]
        review_item = next(
            (item for item in campaign.review_items if item.review_item_id == review_item_id),
            None
        )
        
        if not review_item:
            return {"success": False, "reason": "Review item not found"}
        
        if decision.upper() == "REVOKE":
            review_item.status = ReviewStatus.REVOKED
            await self.identity_provider.revoke_access(
                review_item.user_id,
                review_item.resource_id
            )
        elif decision.upper() == "APPROVE":
            review_item.status = ReviewStatus.APPROVED
        else:
            review_item.status = ReviewStatus.MODIFIED
        
        review_item.reviewed_at = datetime.now()
        review_item.justification = justification
        
        completed_items = sum(1 for item in campaign.review_items if item.status != ReviewStatus.PENDING)
        campaign.completion_rate = completed_items / len(campaign.review_items) if campaign.review_items else 0
        
        agent_metrics.record_event("access_review_agent", "review_decision_processed", {
            "campaign_id": campaign_id,
            "decision": decision,
            "reviewer_id": reviewer_id
        })
        
        return {
            "success": True,
            "review_item_id": review_item_id,
            "status": review_item.status.value,
            "campaign_completion": f"{campaign.completion_rate * 100:.1f}%"
        }
    
    async def get_campaign_status(self, campaign_id: str) -> Dict[str, Any]:
        if campaign_id not in self.campaigns:
            return {"error": "Campaign not found"}
        
        campaign = self.campaigns[campaign_id]
        
        status_counts = {
            "pending": 0,
            "approved": 0,
            "revoked": 0,
            "modified": 0
        }
        
        for item in campaign.review_items:
            status_counts[item.status.value] += 1
        
        return {
            "campaign_id": campaign_id,
            "campaign_name": campaign.campaign_name,
            "status": campaign.status,
            "completion_rate": f"{campaign.completion_rate * 100:.1f}%",
            "total_items": len(campaign.review_items),
            "status_breakdown": status_counts,
            "start_date": campaign.start_date,
            "end_date": campaign.end_date
        }
