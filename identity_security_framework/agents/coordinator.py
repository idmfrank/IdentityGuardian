from typing import Dict, Any
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient
from .access_request_agent import AccessRequestAgent
from .access_review_agent import AccessReviewAgent
from .lifecycle_agent import LifecycleAgent
from .monitoring_agent import MonitoringAgent
from .risk_agent import RiskAgent
from ..utils.telemetry import agent_metrics


class CoordinatorAgent:
    def __init__(
        self,
        model_client: OpenAIChatCompletionClient,
        access_request_agent: AccessRequestAgent,
        access_review_agent: AccessReviewAgent,
        lifecycle_agent: LifecycleAgent,
        monitoring_agent: MonitoringAgent,
        risk_agent: RiskAgent
    ):
        self.access_request_agent = access_request_agent
        self.access_review_agent = access_review_agent
        self.lifecycle_agent = lifecycle_agent
        self.monitoring_agent = monitoring_agent
        self.risk_agent = risk_agent
        
        system_message = """You are the Coordinator Agent for the Identity Security Framework.

Your role is to:
1. Analyze incoming requests and determine the appropriate specialized agent
2. Route tasks to the correct agent based on the request type
3. Coordinate multi-agent workflows when needed
4. Provide high-level summaries and insights
5. Ensure tasks are handled efficiently

Agent Routing Rules:
- Access Requests: Use access_request_agent for new access requests, approvals
- Access Reviews: Use access_review_agent for certification campaigns, reviews
- Lifecycle Events: Use lifecycle_agent for joiners, movers, leavers
- Security Monitoring: Use monitoring_agent for anomaly detection, alerts
- Risk Assessment: Use risk_agent for risk scoring, compliance checks, SoD violations

You can coordinate multiple agents for complex workflows."""

        self.agent = AssistantAgent(
            name="coordinator_agent",
            model_client=model_client,
            system_message=system_message,
            description="Coordinates and routes tasks to specialized identity security agents"
        )
    
    async def process_request(self, request_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        agent_metrics.record_event("coordinator_agent", "request_received", {
            "request_type": request_type
        })
        
        if request_type == "access_request":
            result = await self.access_request_agent.process_request(
                user_id=params.get("user_id"),
                resource_id=params.get("resource_id"),
                resource_type=params.get("resource_type", "application"),
                access_level=params.get("access_level"),
                business_justification=params.get("business_justification")
            )
            
        elif request_type == "approve_request":
            result = await self.access_request_agent.approve_request(
                request_id=params.get("request_id"),
                approver_id=params.get("approver_id")
            )
            
        elif request_type == "create_review_campaign":
            result = await self.access_review_agent.create_campaign(
                campaign_name=params.get("campaign_name"),
                scope=params.get("scope"),
                duration_days=params.get("duration_days", 30)
            )
            
        elif request_type == "review_decision":
            result = await self.access_review_agent.process_review_decision(
                campaign_id=params.get("campaign_id"),
                review_item_id=params.get("review_item_id"),
                decision=params.get("decision"),
                reviewer_id=params.get("reviewer_id"),
                justification=params.get("justification", "")
            )
            
        elif request_type == "joiner":
            result = await self.lifecycle_agent.process_joiner(
                user=params.get("user"),
                start_date=params.get("start_date")
            )
            
        elif request_type == "mover":
            result = await self.lifecycle_agent.process_mover(
                user_id=params.get("user_id"),
                new_department=params.get("new_department"),
                new_role=params.get("new_role"),
                effective_date=params.get("effective_date")
            )
            
        elif request_type == "leaver":
            result = await self.lifecycle_agent.process_leaver(
                user_id=params.get("user_id"),
                termination_date=params.get("termination_date")
            )
            
        elif request_type == "analyze_behavior":
            result = await self.monitoring_agent.analyze_user_behavior(
                user_id=params.get("user_id")
            )
            
        elif request_type == "detect_dormant_accounts":
            result = await self.monitoring_agent.detect_dormant_accounts(
                inactive_days=params.get("inactive_days", 90)
            )
            
        elif request_type == "calculate_risk":
            result = await self.risk_agent.calculate_user_risk_score(
                user_id=params.get("user_id")
            )
            
        elif request_type == "detect_sod_violations":
            result = await self.risk_agent.detect_sod_violations()
            
        elif request_type == "compliance_report":
            result = await self.risk_agent.generate_compliance_report(
                framework=params.get("framework", "SOX")
            )
            
        else:
            result = {"error": f"Unknown request type: {request_type}"}
        
        agent_metrics.record_event("coordinator_agent", "request_completed", {
            "request_type": request_type,
            "success": "error" not in result
        })
        
        return result
    
    def get_available_operations(self) -> Dict[str, Any]:
        return {
            "access_management": [
                "access_request",
                "approve_request"
            ],
            "access_reviews": [
                "create_review_campaign",
                "review_decision"
            ],
            "lifecycle_management": [
                "joiner",
                "mover",
                "leaver"
            ],
            "security_monitoring": [
                "analyze_behavior",
                "detect_dormant_accounts"
            ],
            "risk_management": [
                "calculate_risk",
                "detect_sod_violations",
                "compliance_report"
            ]
        }
