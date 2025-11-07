"""Simple scheduler that polls Sentinel for critical identity events."""

import asyncio

from identity_guardian.agents.monitoring_agent import MonitoringAgent
from identity_guardian.integrations.identity_provider import (
    IdentityProvider,
    get_identity_provider,
)
from identity_guardian.integrations.siem import MockSIEMProvider, SIEMProvider
from identity_guardian.integrations.grc import MockGRCProvider, GRCProvider


async def _build_monitoring_agent() -> MonitoringAgent:
    identity_provider: IdentityProvider = await get_identity_provider()
    siem_provider: SIEMProvider = MockSIEMProvider()
    grc_provider: GRCProvider = MockGRCProvider()

    return MonitoringAgent(
        None,
        identity_provider,
        siem_provider,
        grc_provider,
    )


async def run_watcher(poll_interval_seconds: int = 300) -> None:
    agent = await _build_monitoring_agent()

    while True:
        results = await agent.watch_for_critical_events()
        if results:
            print("Auto-block actions:")
            for entry in results:
                print(entry)
        await asyncio.sleep(poll_interval_seconds)


if __name__ == "__main__":  # pragma: no cover - manual scheduler
    asyncio.run(run_watcher())
