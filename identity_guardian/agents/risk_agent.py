from typing import Dict, Any, List
from datetime import datetime
import uuid
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient
from ..models.identity import IdentityRisk, RiskLevel
from ..integrations.identity_provider import IdentityProvider
from ..integrations.grc import GRCProvider
from ..integrations.siem import SIEMProvider
from ..utils.telemetry import agent_metrics


class RiskAgent:
    def __init__(
        self,
        model_client: OpenAIChatCompletionClient,
        identity_provider: IdentityProvider,
        grc_provider: GRCProvider,
        siem_provider: SIEMProvider
    ):
        self.identity_provider = identity_provider
        self.grc_provider = grc_provider
        self.siem_provider = siem_provider
        self.risks = {}
        
        system_message = """You are an Identity Risk Management Agent specialized in compliance and risk assessment.

Your responsibilities:
1. Calculate comprehensive identity risk scores
2. Detect policy violations and SoD (Segregation of Duties) conflicts
3. Provide compliance insights and reporting
4. Identify high-risk access patterns
5. Recommend risk mitigation strategies
6. Integrate with GRC platforms for governance

Risk assessment factors:
- User role and privilege level
- Access to sensitive resources
- Compliance policy violations
- Historical behavior patterns
- SoD conflicts
- Excessive permissions

Provide clear risk assessments with actionable remediation steps."""

        self.agent = AssistantAgent(
            name="risk_agent",
            model_client=model_client,
            system_message=system_message,
            description="Assesses identity risks and ensures compliance"
        )
    
    async def calculate_user_risk_score(self, user_id: str) -> Dict[str, Any]:
        agent_metrics.record_event("risk_agent", "risk_assessment", {
            "user_id": user_id
        })
        
        user = await self.identity_provider.get_user(user_id)
        if not user:
            return {"error": "User not found"}
        
        risk_factors = []
        risk_score = 0.0
        
        user_access = await self.identity_provider.get_user_access(user_id)
        
        privileged_access_count = 0
        sensitive_resource_count = 0
        
        for access in user_access:
            resource_id = access.get("resource_id", "")
            access_level = access.get("access_level", "")
            
            if "admin" in access_level.lower() or "privileged" in access_level.lower():
                privileged_access_count += 1
            
            if any(sensitive in resource_id.lower() for sensitive in ["pii", "financial", "production"]):
                sensitive_resource_count += 1
            
            compliance_check = await self.grc_provider.check_policy_compliance(
                user_id, resource_id, access_level
            )
            
            if not compliance_check.get("compliant", True):
                for violation in compliance_check.get("violations", []):
                    risk_factors.append({
                        "type": "policy_violation",
                        "description": violation["violation"],
                        "severity": violation["severity"],
                        "resource": resource_id
                    })
                    risk_score += 0.15
        
        if privileged_access_count > 0:
            risk_factors.append({
                "type": "privileged_access",
                "description": f"User has {privileged_access_count} privileged access grants",
                "severity": "medium"
            })
            risk_score += 0.2 * min(privileged_access_count, 3)
        
        if sensitive_resource_count > 0:
            risk_factors.append({
                "type": "sensitive_data_access",
                "description": f"Access to {sensitive_resource_count} sensitive resources",
                "severity": "medium"
            })
            risk_score += 0.15 * min(sensitive_resource_count, 3)
        
        behavior_baseline = await self.siem_provider.get_user_behavior_baseline(user_id)
        if behavior_baseline.get("baseline_risk_score", 0) > 0.5:
            risk_factors.append({
                "type": "behavioral_risk",
                "description": "Elevated baseline behavioral risk",
                "severity": "medium"
            })
            risk_score += 0.2
        
        risk_score = min(risk_score, 1.0)
        
        risk_level = self._determine_risk_level(risk_score)
        
        risk_id = str(uuid.uuid4())
        identity_risk = IdentityRisk(
            risk_id=risk_id,
            user_id=user_id,
            risk_type="comprehensive_assessment",
            risk_level=risk_level,
            risk_score=risk_score,
            detected_at=datetime.now(),
            description=f"Identity risk assessment for {user.username}",
            indicators=[f"{rf['type']}: {rf['description']}" for rf in risk_factors],
            remediation_steps=self._generate_remediation_steps(risk_factors),
            status="open"
        )
        
        self.risks[risk_id] = identity_risk
        
        await self.grc_provider.log_compliance_event({
            "event_type": "risk_assessment",
            "user_id": user_id,
            "risk_score": risk_score,
            "risk_level": risk_level.value
        })
        
        agent_metrics.record_event("risk_agent", "risk_calculated", {
            "user_id": user_id,
            "risk_score": risk_score,
            "risk_level": risk_level.value
        })
        
        return {
            "risk_id": risk_id,
            "user_id": user_id,
            "risk_score": round(risk_score, 2),
            "risk_level": risk_level.value,
            "risk_factors": risk_factors,
            "remediation_steps": identity_risk.remediation_steps
        }
    
    def _determine_risk_level(self, risk_score: float) -> RiskLevel:
        if risk_score >= 0.75:
            return RiskLevel.CRITICAL
        elif risk_score >= 0.5:
            return RiskLevel.HIGH
        elif risk_score >= 0.3:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _generate_remediation_steps(self, risk_factors: List[Dict[str, Any]]) -> List[str]:
        steps = []
        
        if any(rf["type"] == "policy_violation" for rf in risk_factors):
            steps.append("Review and remediate policy violations immediately")
        
        if any(rf["type"] == "privileged_access" for rf in risk_factors):
            steps.append("Conduct privileged access review and remove unnecessary admin rights")
        
        if any(rf["type"] == "sensitive_data_access" for rf in risk_factors):
            steps.append("Verify business need for sensitive data access")
        
        if any(rf["type"] == "behavioral_risk" for rf in risk_factors):
            steps.append("Investigate recent user activity for anomalies")
        
        steps.append("Schedule access review with user's manager")
        
        return steps
    
    async def detect_sod_violations(self) -> Dict[str, Any]:
        agent_metrics.record_event("risk_agent", "sod_check", {})
        
        users = await self.identity_provider.list_users({"status": "active"})
        violations = []
        
        policies = await self.grc_provider.get_risk_policies()
        sod_policies = [p for p in policies if "segregation" in p["name"].lower()]
        
        for user in users:
            for policy in sod_policies:
                conflicting_role_sets = policy.get("rules", {}).get("conflicting_roles", [])
                
                for conflict_set in conflicting_role_sets:
                    user_has_conflicts = all(role in user.roles for role in conflict_set)
                    
                    if user_has_conflicts:
                        violations.append({
                            "user_id": user.user_id,
                            "username": user.username,
                            "policy_id": policy["policy_id"],
                            "policy_name": policy["name"],
                            "conflicting_roles": conflict_set,
                            "severity": "high"
                        })
        
        agent_metrics.record_event("risk_agent", "sod_violations_found", {
            "count": len(violations)
        })
        
        return {
            "violations_found": len(violations),
            "violations": violations
        }
    
    async def generate_compliance_report(self, framework: str = "SOX") -> Dict[str, Any]:
        agent_metrics.record_event("risk_agent", "compliance_report", {
            "framework": framework
        })
        
        users = await self.identity_provider.list_users({"status": "active"})
        
        total_users = len(users)
        high_risk_users = 0
        policy_violations = 0
        
        for user in users:
            risk_assessment = await self.calculate_user_risk_score(user.user_id)
            
            if risk_assessment.get("risk_level") in ["high", "critical"]:
                high_risk_users += 1
            
            policy_violations += len([
                rf for rf in risk_assessment.get("risk_factors", [])
                if rf["type"] == "policy_violation"
            ])
        
        frameworks = await self.grc_provider.get_compliance_frameworks()
        
        return {
            "framework": framework,
            "report_date": datetime.now(),
            "summary": {
                "total_users_assessed": total_users,
                "high_risk_users": high_risk_users,
                "policy_violations": policy_violations,
                "compliance_rate": f"{((total_users - high_risk_users) / total_users * 100):.1f}%"
            },
            "supported_frameworks": frameworks,
            "recommendations": [
                "Review all high-risk user access",
                "Remediate policy violations",
                "Conduct quarterly access reviews"
            ]
        }
