"""Azure Sentinel (Microsoft Sentinel) monitoring integration."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from azure.identity.aio import AzureCliCredential
from azure.monitor.query.aio import LogsQueryClient


logger = logging.getLogger(__name__)


class SentinelMonitor:
    """Lightweight wrapper for running KQL queries against Microsoft Sentinel."""

    def __init__(self, workspace_id: str) -> None:
        if not workspace_id:
            raise ValueError("Sentinel workspace ID must be provided")
        self.workspace_id = workspace_id
        self._credential = AzureCliCredential()
        self._client = LogsQueryClient(self._credential)

    async def close(self) -> None:
        await self._credential.close()

    async def query_risky_signins(self, user_id: str, hours: int = 24) -> List[Dict[str, Any]]:
        query = f"""
        SigninLogs
        | where TimeGenerated > ago({hours}h)
        | where UserPrincipalName == "{user_id}"
        | where RiskLevelDuringSignIn != "none" or RiskLevelAggregated != "none"
        | project TimeGenerated, IPAddress, RiskLevelDuringSignIn, RiskLevelAggregated
        """
        try:
            result = await self._client.query_workspace(self.workspace_id, query, timespan=None)
        except Exception as exc:
            logger.error("Sentinel risky sign-in query failed: %s", exc, exc_info=True)
            return []

        tables = getattr(result, "tables", []) or []
        if not tables:
            return []

        return [row.as_dict() for row in tables[0].rows]

    async def query_privilege_escalation(self, user_id: str, hours: int = 24) -> List[Dict[str, Any]]:
        query = f"""
        AuditLogs
        | where TimeGenerated > ago({hours}h)
        | where InitiatedBy.user.userPrincipalName == "{user_id}"
        | where OperationName contains "role"
        | project TimeGenerated, OperationName, TargetResources
        """
        try:
            result = await self._client.query_workspace(self.workspace_id, query, timespan=None)
        except Exception as exc:
            logger.error("Sentinel privilege escalation query failed: %s", exc, exc_info=True)
            return []

        tables = getattr(result, "tables", []) or []
        if not tables:
            return []

        return [row.as_dict() for row in tables[0].rows]
