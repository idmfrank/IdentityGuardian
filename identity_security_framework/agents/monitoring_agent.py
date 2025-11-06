from typing import Dict, Any, List
from datetime import datetime
import uuid
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient
from ..models.identity import SecurityAlert
from ..integrations.identity_provider import IdentityProvider
from ..integrations.siem import SIEMProvider
from ..utils.telemetry import agent_metrics


class MonitoringAgent:
    def __init__(
        self,
        model_client: OpenAIChatCompletionClient,
        identity_provider: IdentityProvider,
        siem_provider: SIEMProvider
    ):
        self.identity_provider = identity_provider
        self.siem_provider = siem_provider
        self.alerts = {}
        
        system_message = """You are an Identity Monitoring Agent specialized in threat detection.

Your responsibilities:
1. Detect anomalous access patterns and behaviors
2. Identify privilege escalation attempts
3. Find orphaned and dormant accounts
4. Monitor for unauthorized access attempts
5. Alert on suspicious identity-related activities
6. Integrate with SIEM for correlation

Monitoring focus areas:
- Login patterns (unusual times, locations, frequencies)
- Access patterns (unusual resources, excessive access)
- Privilege changes (unexpected escalations)
- Account anomalies (dormant accounts, orphaned accounts)
- Policy violations (failed compliance checks)

Provide clear, actionable alerts with context and recommended response actions."""

        self.agent = AssistantAgent(
            name="monitoring_agent",
            model_client=model_client,
            system_message=system_message,
            description="Detects anomalous access patterns and security threats"
        )
    
    async def analyze_user_behavior(self, user_id: str) -> Dict[str, Any]:
        agent_metrics.record_event("monitoring_agent", "behavior_analysis", {
            "user_id": user_id
        })
        
        user = await self.identity_provider.get_user(user_id)
        if not user:
            return {"error": "User not found"}
        
        recent_events = await self.siem_provider.query_events(user_id, time_range=24)
        baseline = await self.siem_provider.get_user_behavior_baseline(user_id)
        
        anomalies = []
        
        login_count = sum(1 for e in recent_events if e["event_type"] == "login")
        if login_count > baseline["avg_daily_logins"] * 3:
            anomalies.append({
                "type": "excessive_logins",
                "severity": "medium",
                "description": f"Unusual login frequency: {login_count} vs baseline {baseline['avg_daily_logins']}"
            })
        
        privilege_escalations = [e for e in recent_events if e["event_type"] == "privilege_escalation"]
        if privilege_escalations:
            anomalies.append({
                "type": "privilege_escalation",
                "severity": "high",
                "description": f"Detected {len(privilege_escalations)} privilege escalation events"
            })
        
        data_exports = [e for e in recent_events if e["event_type"] == "data_export"]
        if data_exports:
            anomalies.append({
                "type": "data_export",
                "severity": "high",
                "description": f"Detected {len(data_exports)} data export events"
            })
        
        if anomalies:
            alert = await self._create_alert(user_id, anomalies)
            return {
                "user_id": user_id,
                "anomalies_detected": len(anomalies),
                "alert_id": alert["alert_id"],
                "anomalies": anomalies,
                "risk_level": "high" if any(a["severity"] == "high" for a in anomalies) else "medium"
            }
        
        return {
            "user_id": user_id,
            "anomalies_detected": 0,
            "status": "normal"
        }
    
    async def detect_dormant_accounts(self, inactive_days: int = 90) -> Dict[str, Any]:
        agent_metrics.record_event("monitoring_agent", "dormant_account_scan", {
            "inactive_threshold": inactive_days
        })
        
        users = await self.identity_provider.list_users({"status": "active"})
        dormant_accounts = []
        
        for user in users:
            recent_events = await self.siem_provider.query_events(user.user_id, time_range=inactive_days * 24)
            
            if len(recent_events) == 0:
                dormant_accounts.append({
                    "user_id": user.user_id,
                    "username": user.username,
                    "department": user.department,
                    "last_activity": "None in last 90 days",
                    "recommendation": "Disable account"
                })
        
        if dormant_accounts:
            await self.siem_provider.send_alert({
                "alert_type": "dormant_accounts",
                "severity": "medium",
                "description": f"Found {len(dormant_accounts)} dormant accounts",
                "dormant_count": len(dormant_accounts)
            })
        
        return {
            "dormant_accounts_found": len(dormant_accounts),
            "accounts": dormant_accounts[:10],
            "total_users_scanned": len(users)
        }
    
    async def detect_orphaned_accounts(self) -> Dict[str, Any]:
        agent_metrics.record_event("monitoring_agent", "orphaned_account_scan", {})
        
        users = await self.identity_provider.list_users({"status": "active"})
        orphaned_accounts = []
        
        for user in users:
            if not user.manager_id:
                orphaned_accounts.append({
                    "user_id": user.user_id,
                    "username": user.username,
                    "department": user.department,
                    "issue": "No manager assigned",
                    "recommendation": "Assign manager or disable account"
                })
        
        return {
            "orphaned_accounts_found": len(orphaned_accounts),
            "accounts": orphaned_accounts
        }
    
    async def monitor_privilege_escalation(self) -> Dict[str, Any]:
        agent_metrics.record_event("monitoring_agent", "privilege_escalation_monitor", {})
        
        users = await self.identity_provider.list_users({"status": "active"})
        escalation_events = []
        
        for user in users:
            recent_events = await self.siem_provider.query_events(user.user_id, time_range=24)
            
            priv_events = [e for e in recent_events if e["event_type"] == "privilege_escalation"]
            
            if priv_events:
                escalation_events.append({
                    "user_id": user.user_id,
                    "username": user.username,
                    "event_count": len(priv_events),
                    "timestamps": [e["timestamp"] for e in priv_events[:3]]
                })
                
                await self._create_alert(user.user_id, [{
                    "type": "privilege_escalation",
                    "severity": "critical",
                    "description": f"Detected privilege escalation attempts"
                }])
        
        return {
            "users_with_escalations": len(escalation_events),
            "escalation_events": escalation_events
        }
    
    async def _create_alert(self, user_id: str, anomalies: List[Dict[str, Any]]) -> Dict[str, Any]:
        alert_id = str(uuid.uuid4())
        
        severity = "critical" if any(a["severity"] == "high" for a in anomalies) else "medium"
        
        recommended_actions = [
            "Review user activity logs",
            "Contact user to verify activity",
            "Consider temporary access suspension"
        ]
        
        if any(a["type"] == "privilege_escalation" for a in anomalies):
            recommended_actions.append("Immediate security team investigation required")
        
        alert = SecurityAlert(
            alert_id=alert_id,
            alert_type="identity_anomaly",
            severity=severity,
            user_id=user_id,
            detected_at=datetime.now(),
            description=f"Detected {len(anomalies)} security anomalies",
            indicators={a["type"]: a["description"] for a in anomalies},
            recommended_actions=recommended_actions,
            status="new"
        )
        
        self.alerts[alert_id] = alert
        
        await self.siem_provider.send_alert({
            "alert_id": alert_id,
            "user_id": user_id,
            "severity": severity,
            "anomalies": anomalies
        })
        
        agent_metrics.record_event("monitoring_agent", "alert_created", {
            "alert_id": alert_id,
            "severity": severity
        })
        
        return {
            "alert_id": alert_id,
            "severity": severity,
            "recommended_actions": recommended_actions
        }
    
    async def get_alert(self, alert_id: str) -> Dict[str, Any]:
        if alert_id not in self.alerts:
            return {"error": "Alert not found"}
        
        alert = self.alerts[alert_id]
        return {
            "alert_id": alert.alert_id,
            "alert_type": alert.alert_type,
            "severity": alert.severity,
            "user_id": alert.user_id,
            "detected_at": alert.detected_at,
            "description": alert.description,
            "indicators": alert.indicators,
            "recommended_actions": alert.recommended_actions,
            "status": alert.status
        }
