from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
import uuid
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient
from ..models.identity import SecurityAlert
from ..integrations.identity_provider import IdentityProvider
from ..integrations.siem import SIEMProvider
from ..integrations.sentinel import SentinelMonitor
from ..integrations.grc import GRCProvider, MockGRCProvider
from .risk_agent import RiskAgent
from ..config.settings import get_settings
from ..utils.telemetry import agent_metrics


class MonitoringAgent:
    def __init__(
        self,
        model_client: Optional[OpenAIChatCompletionClient],
        identity_provider: IdentityProvider,
        siem_provider: SIEMProvider,
        grc_provider: Optional[GRCProvider] = None,
    ):
        self._logger = logging.getLogger(__name__)
        self.model_client = model_client
        self.identity_provider = identity_provider
        self.siem_provider = siem_provider
        self.grc_provider = grc_provider or MockGRCProvider()
        self.alerts = {}
        self._settings = get_settings()
        self._sentinel_monitor: Optional[SentinelMonitor] = None

        workspace_id = getattr(self._settings, "SENTINEL_WORKSPACE_ID", "")
        if workspace_id:
            try:
                self._sentinel_monitor = SentinelMonitor(workspace_id)
            except Exception as exc:
                self._logger.warning(
                    "Failed to initialize Sentinel monitor for workspace %s: %s",
                    workspace_id,
                    exc,
                )
                self._sentinel_monitor = None
        
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

        self.agent: Optional[AssistantAgent] = None
        if model_client is not None:
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
        
        sentinel_summary = await self.get_sentinel_summary(user_id)

        if anomalies:
            alert = await self._create_alert(user_id, anomalies)
            return {
                "user_id": user_id,
                "anomalies_detected": len(anomalies),
                "alert_id": alert["alert_id"],
                "anomalies": anomalies,
                "risk_level": "high" if any(a["severity"] == "high" for a in anomalies) else "medium",
                "sentinel": sentinel_summary,
            }

        return {
            "user_id": user_id,
            "anomalies_detected": 0,
            "status": "normal",
            "sentinel": sentinel_summary,
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

    async def get_sentinel_summary(self, user_id: str) -> Dict[str, Any]:
        """Return Sentinel findings for a given user if Sentinel is configured."""

        if not self._sentinel_monitor:
            return {"enabled": False}

        risky_signins = await self._sentinel_monitor.query_risky_signins(user_id)
        escalations = await self._sentinel_monitor.query_privilege_escalation(user_id)
        sentinel_score = min(len(risky_signins) * 30 + len(escalations) * 50, 100)

        return {
            "enabled": True,
            "workspace_id": self._sentinel_monitor.workspace_id,
            "risky_signins": risky_signins,
            "privilege_escalations": escalations,
            "sentinel_risk_score": sentinel_score,
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

    async def watch_for_critical_events(self) -> List[Dict[str, Any]]:
        """Query Sentinel for correlated critical events and auto-block high-risk users."""

        if not self._sentinel_monitor:
            self._logger.debug("Sentinel monitor not configured; skipping critical event watch")
            return []

        try:
            candidates = await self._sentinel_monitor.query_auto_block_candidates()
        except Exception as exc:
            self._logger.error("Failed to query Sentinel for critical events: %s", exc, exc_info=True)
            return []

        if not candidates:
            return []

        risk_agent = RiskAgent(
            self.model_client,
            self.identity_provider,
            self.grc_provider,
            self.siem_provider,
        )
        risk_agent._sentinel_monitor = self._sentinel_monitor

        results: List[Dict[str, Any]] = []
        for user in candidates:
            try:
                outcome = await risk_agent.calculate_and_mitigate(user)
                results.append(outcome)
            except Exception as exc:
                self._logger.error("Auto-block workflow failed for %s: %s", user, exc, exc_info=True)

        return results
