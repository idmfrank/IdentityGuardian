import sys
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch


class _DummyCredential:  # pragma: no cover - dependency shim
    def __init__(self, *args, **kwargs):
        pass

    async def close(self):  # pragma: no cover - shim
        return None


class _DummyAPIVersion:  # pragma: no cover - shim
    BETA = "beta"


class _DummyGraphClient:  # pragma: no cover - shim
    def __init__(self, *args, **kwargs):
        pass


msgraph_core = SimpleNamespace(APIVersion=_DummyAPIVersion)
msgraph_module = SimpleNamespace(core=msgraph_core, GraphServiceClient=_DummyGraphClient)

sys.modules.setdefault("msgraph", msgraph_module)
sys.modules.setdefault("msgraph.core", msgraph_core)

azure_identity_aio = SimpleNamespace(
    AzureCliCredential=_DummyCredential,
    ManagedIdentityCredential=_DummyCredential,
)

azure_monitor_query_aio = SimpleNamespace(LogsQueryClient=_DummyCredential)

azure_module = sys.modules.setdefault("azure", SimpleNamespace())
setattr(azure_module, "identity", SimpleNamespace(aio=azure_identity_aio))
setattr(azure_module, "monitor", SimpleNamespace(query=SimpleNamespace(aio=azure_monitor_query_aio)))

sys.modules.setdefault("azure.identity", SimpleNamespace(aio=azure_identity_aio))
sys.modules.setdefault("azure.identity.aio", azure_identity_aio)
sys.modules.setdefault("azure.monitor", azure_module.monitor)
sys.modules.setdefault("azure.monitor.query", azure_module.monitor.query)
sys.modules.setdefault("azure.monitor.query.aio", azure_monitor_query_aio)

from identity_guardian.agents.risk_agent import RiskAgent
from identity_guardian.integrations.identity_provider import MockIdentityProvider
from identity_guardian.integrations.grc import MockGRCProvider
from identity_guardian.integrations.siem import SIEMProvider


class DummySIEMProvider(SIEMProvider):
    async def send_alert(self, alert):  # pragma: no cover - simple stub
        return True

    async def query_events(self, user_id, time_range=24):  # pragma: no cover - stub
        return []

    async def get_user_behavior_baseline(self, user_id):  # pragma: no cover - stub
        return {"baseline_risk_score": 0}


class HighRiskIdentityProvider(MockIdentityProvider):
    def __init__(self):
        super().__init__()
        self.disabled_users = []

    async def get_user_risk(self, user_id: str) -> str:
        return "Identity Protection Risk: high"

    async def disable_user(self, user_id: str, reason: str) -> str:
        self.disabled_users.append((user_id, reason))
        return f"User {user_id} disabled. Reason: {reason}"


class AutoBlockTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.identity_provider = HighRiskIdentityProvider()
        self.grc_provider = MockGRCProvider()
        self.siem_provider = DummySIEMProvider()
        self.agent = RiskAgent(None, self.identity_provider, self.grc_provider, self.siem_provider)

    async def test_auto_block_triggers_disable_and_alert(self):
        async def fake_summary(_self, _user_id):
            return {
                "risky_signins": [{}],
                "privilege_escalations": [{}],
                "sentinel_risk_score": 20,
            }

        with patch("identity_guardian.integrations.teams_bot.TeamsApprovalBot.send_alert", new_callable=AsyncMock) as alert_mock:
            self.agent._get_sentinel_summary = fake_summary.__get__(self.agent, RiskAgent)
            result = await self.agent.calculate_and_mitigate("user001")

        self.assertEqual(result["action"], "blocked")
        self.assertTrue(self.identity_provider.disabled_users)
        self.assertGreaterEqual(result["total_risk_score"], 90)
        alert_mock.assert_awaited_once()

    async def test_auto_block_not_triggered_below_threshold(self):
        async def low_summary(_self, _user_id):
            return {
                "risky_signins": [],
                "privilege_escalations": [],
                "sentinel_risk_score": 5,
            }

        with patch("identity_guardian.integrations.teams_bot.TeamsApprovalBot.send_alert", new_callable=AsyncMock) as alert_mock:
            self.agent._get_sentinel_summary = low_summary.__get__(self.agent, RiskAgent)
            result = await self.agent.calculate_and_mitigate("user001")

        self.assertEqual(result["action"], "monitored")
        self.assertFalse(self.identity_provider.disabled_users)
        alert_mock.assert_not_called()


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
