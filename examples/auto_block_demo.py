"""Run the auto-block workflow with mock providers and show the CA block response."""

import asyncio
from pprint import pprint

from identity_guardian.agents.risk_agent import RiskAgent
from identity_guardian.integrations.identity_provider import MockIdentityProvider
from identity_guardian.integrations.grc import MockGRCProvider
from identity_guardian.integrations.siem import MockSIEMProvider


class DemoIdentityProvider(MockIdentityProvider):
    async def get_user_risk(self, user_id: str) -> str:  # pragma: no cover - demo helper
        return "Identity Protection Risk: critical"


async def main() -> None:
    identity_provider = DemoIdentityProvider()
    grc_provider = MockGRCProvider()
    siem_provider = MockSIEMProvider()

    agent = RiskAgent(None, identity_provider, grc_provider, siem_provider)

    result = await agent.calculate_and_mitigate("attacker@contoso.com")
    pprint(result)


if __name__ == "__main__":  # pragma: no cover - manual demo
    asyncio.run(main())
