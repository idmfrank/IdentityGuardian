"""Mock coordinator for running without OpenAI API key"""

from typing import Dict, Any
from datetime import datetime, timedelta
import uuid
from ..models.identity import User
from ..integrations.identity_provider import IdentityProvider
from ..integrations.itsm import ITSMProvider
from ..integrations.siem import SIEMProvider
from ..integrations.grc import GRCProvider
from ..utils.telemetry import agent_metrics


class MockCoordinator:
    """Simplified coordinator that works without LLM API keys"""
    
    def __init__(
        self,
        identity_provider: IdentityProvider,
        itsm_provider: ITSMProvider,
        siem_provider: SIEMProvider,
        grc_provider: GRCProvider
    ):
        self.identity_provider = identity_provider
        self.itsm_provider = itsm_provider
        self.siem_provider = siem_provider
        self.grc_provider = grc_provider
        self.pending_requests = {}
        self.campaigns = {}
        self.lifecycle_events = {}
        self.alerts = {}
        self.risks = {}
    
    async def process_request(self, request_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        agent_metrics.record_event("mock_coordinator", "request_received", {
            "request_type": request_type
        })
        
        if request_type == "access_request":
            return await self._mock_access_request(params)
        elif request_type == "create_review_campaign":
            return await self._mock_review_campaign(params)
        elif request_type == "joiner":
            return await self._mock_joiner(params)
        elif request_type == "calculate_risk":
            return await self._mock_risk_assessment(params)
        elif request_type == "analyze_behavior":
            return await self._mock_behavior_analysis(params)
        elif request_type == "detect_dormant_accounts":
            return await self._mock_dormant_detection(params)
        elif request_type == "detect_sod_violations":
            return await self._mock_sod_detection()
        elif request_type == "compliance_report":
            return await self._mock_compliance_report(params)
        else:
            return {"error": f"Unknown request type: {request_type}"}
    
    async def _mock_access_request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        user_id = params.get("user_id")
        resource_id = params.get("resource_id")
        access_level = params.get("access_level")
        
        user = await self.identity_provider.get_user(user_id)
        if not user:
            return {"status": "rejected", "reason": "User not found"}
        
        compliance_check = await self.grc_provider.check_policy_compliance(
            user_id, resource_id, access_level
        )
        
        risk_score = 0.3
        if "admin" in access_level.lower():
            risk_score += 0.3
        if not compliance_check.get("compliant", True):
            risk_score += 0.2
        if any(s in resource_id.lower() for s in ["financial", "pii", "production"]):
            risk_score += 0.2
        
        request_id = str(uuid.uuid4())
        approvers = [user.manager_id] if user.manager_id else []
        
        if risk_score > 0.5:
            approvers.append("security_team")
        
        ticket_id = await self.itsm_provider.create_ticket(
            title=f"Access Request: {user.username} -> {resource_id}",
            description=f"Access request for {access_level} to {resource_id}",
            category="Access Request",
            priority="High" if risk_score > 0.7 else "Medium"
        )
        
        recommendation = "APPROVE - Request appears reasonable" if risk_score < 0.5 else "REVIEW - Elevated risk, additional scrutiny recommended"
        
        return {
            "request_id": request_id,
            "status": "pending_approval",
            "risk_score": round(risk_score, 2),
            "policy_violations": [v["violation"] for v in compliance_check.get("violations", [])],
            "approvers": approvers,
            "ticket_id": ticket_id,
            "recommendation": recommendation
        }
    
    async def _mock_review_campaign(self, params: Dict[str, Any]) -> Dict[str, Any]:
        campaign_id = str(uuid.uuid4())
        users = await self.identity_provider.list_users()
        
        review_items_count = 0
        for user in users:
            user_access = await self.identity_provider.get_user_access(user.user_id)
            review_items_count += len(user_access)
        
        start_date = datetime.now()
        end_date = start_date + timedelta(days=params.get("duration_days", 30))
        
        return {
            "campaign_id": campaign_id,
            "campaign_name": params.get("campaign_name"),
            "review_items_count": review_items_count,
            "start_date": start_date,
            "end_date": end_date
        }
    
    async def _mock_joiner(self, params: Dict[str, Any]) -> Dict[str, Any]:
        user = params.get("user")
        event_id = str(uuid.uuid4())
        
        provisioning_tasks = [
            "Create user account in identity provider",
            "Provision baseline access for role",
            "Add to department groups",
            "Setup email and collaboration tools",
            "Grant access to common resources"
        ]
        
        if "engineer" in user.department.lower():
            provisioning_tasks.extend([
                "Grant code repository access",
                "Provision development environment"
            ])
        
        ticket_id = await self.itsm_provider.create_ticket(
            title=f"New Hire: {user.first_name} {user.last_name}",
            description=f"Onboard new hire in {user.department}",
            category="Provisioning",
            priority="High"
        )
        
        return {
            "event_id": event_id,
            "event_type": "joiner",
            "user_id": user.user_id,
            "status": "completed",
            "provisioning_tasks": provisioning_tasks,
            "ticket_id": ticket_id
        }
    
    async def _mock_risk_assessment(self, params: Dict[str, Any]) -> Dict[str, Any]:
        user_id = params.get("user_id")
        user = await self.identity_provider.get_user(user_id)
        
        if not user:
            return {"error": "User not found"}
        
        user_access = await self.identity_provider.get_user_access(user_id)
        
        risk_factors = []
        risk_score = 0.3
        
        privileged_count = sum(1 for a in user_access if "admin" in a.get("access_level", "").lower())
        if privileged_count > 0:
            risk_factors.append({
                "type": "privileged_access",
                "description": f"User has {privileged_count} privileged access grants",
                "severity": "medium"
            })
            risk_score += 0.2
        
        sensitive_count = sum(1 for a in user_access if any(s in a.get("resource_id", "").lower() for s in ["pii", "financial"]))
        if sensitive_count > 0:
            risk_factors.append({
                "type": "sensitive_data_access",
                "description": f"Access to {sensitive_count} sensitive resources",
                "severity": "medium"
            })
            risk_score += 0.15
        
        risk_level = "critical" if risk_score >= 0.75 else "high" if risk_score >= 0.5 else "medium" if risk_score >= 0.3 else "low"
        
        remediation_steps = [
            "Review privileged access grants",
            "Verify business need for sensitive data access",
            "Schedule access review with manager"
        ]
        
        return {
            "risk_id": str(uuid.uuid4()),
            "user_id": user_id,
            "risk_score": round(risk_score, 2),
            "risk_level": risk_level,
            "risk_factors": risk_factors,
            "remediation_steps": remediation_steps
        }
    
    async def _mock_behavior_analysis(self, params: Dict[str, Any]) -> Dict[str, Any]:
        user_id = params.get("user_id")
        
        recent_events = await self.siem_provider.query_events(user_id, time_range=24)
        baseline = await self.siem_provider.get_user_behavior_baseline(user_id)
        
        anomalies = []
        login_count = sum(1 for e in recent_events if e["event_type"] == "login")
        
        if login_count > baseline["avg_daily_logins"] * 2:
            anomalies.append({
                "type": "excessive_logins",
                "severity": "medium",
                "description": f"Unusual login frequency: {login_count} vs baseline {baseline['avg_daily_logins']}"
            })
        
        if anomalies:
            return {
                "user_id": user_id,
                "anomalies_detected": len(anomalies),
                "alert_id": str(uuid.uuid4()),
                "anomalies": anomalies,
                "risk_level": "medium"
            }
        
        return {
            "user_id": user_id,
            "anomalies_detected": 0,
            "status": "normal"
        }
    
    async def _mock_dormant_detection(self, params: Dict[str, Any]) -> Dict[str, Any]:
        users = await self.identity_provider.list_users({"status": "active"})
        
        dormant_accounts = [
            {
                "user_id": "user999",
                "username": "old.user",
                "department": "IT",
                "last_activity": "None in last 90 days",
                "recommendation": "Disable account"
            }
        ]
        
        return {
            "dormant_accounts_found": len(dormant_accounts),
            "accounts": dormant_accounts,
            "total_users_scanned": len(users)
        }
    
    async def _mock_sod_detection(self) -> Dict[str, Any]:
        return {
            "violations_found": 0,
            "violations": []
        }
    
    async def _mock_compliance_report(self, params: Dict[str, Any]) -> Dict[str, Any]:
        framework = params.get("framework", "SOX")
        users = await self.identity_provider.list_users({"status": "active"})
        
        return {
            "framework": framework,
            "report_date": datetime.now(),
            "summary": {
                "total_users_assessed": len(users),
                "high_risk_users": 1,
                "policy_violations": 2,
                "compliance_rate": "96.7%"
            },
            "supported_frameworks": ["SOX", "GDPR", "HIPAA", "ISO27001"],
            "recommendations": [
                "Review all high-risk user access",
                "Remediate policy violations",
                "Conduct quarterly access reviews"
            ]
        }
    
    def get_available_operations(self) -> Dict[str, Any]:
        return {
            "access_management": ["access_request"],
            "access_reviews": ["create_review_campaign"],
            "lifecycle_management": ["joiner"],
            "security_monitoring": ["analyze_behavior", "detect_dormant_accounts"],
            "risk_management": ["calculate_risk", "detect_sod_violations", "compliance_report"]
        }
