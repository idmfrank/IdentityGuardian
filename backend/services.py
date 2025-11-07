from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from autogen_ext.models.openai import OpenAIChatCompletionClient

from identity_guardian.agents.access_request_agent import AccessRequestAgent
from identity_guardian.agents.access_review_agent import AccessReviewAgent
from identity_guardian.agents.coordinator import CoordinatorAgent
from identity_guardian.agents.lifecycle_agent import LifecycleAgent
from identity_guardian.agents.mock_coordinator import MockCoordinator
from identity_guardian.agents.monitoring_agent import MonitoringAgent
from identity_guardian.agents.risk_agent import RiskAgent
from identity_guardian.config.settings import get_settings
from identity_guardian.integrations.grc import GRCProvider, MockGRCProvider
from identity_guardian.integrations.identity_provider import (
    IdentityProvider,
    MockIdentityProvider,
    get_identity_provider,
)
from identity_guardian.integrations.itsm import ITSMProvider, MockITSMProvider
from identity_guardian.integrations.siem import MockSIEMProvider, SIEMProvider


@dataclass
class DashboardServices:
    settings: Any
    identity_provider: IdentityProvider
    itsm_provider: ITSMProvider
    siem_provider: SIEMProvider
    grc_provider: GRCProvider
    coordinator: CoordinatorAgent | MockCoordinator
    mock_mode: bool
    access_request_agent: Optional[AccessRequestAgent] = None
    access_review_agent: Optional[AccessReviewAgent] = None
    lifecycle_agent: Optional[LifecycleAgent] = None
    monitoring_agent: Optional[MonitoringAgent] = None
    risk_agent: Optional[RiskAgent] = None
    model_client: Optional[OpenAIChatCompletionClient] = None


async def init_services() -> DashboardServices:
    """Initialise shared IdentityGuardian agent services for the API."""

    settings = get_settings()

    try:
        identity_provider = await get_identity_provider()
    except Exception:
        identity_provider = MockIdentityProvider()
    if identity_provider is None:
        identity_provider = MockIdentityProvider()

    itsm_provider: ITSMProvider = MockITSMProvider()
    siem_provider: SIEMProvider = MockSIEMProvider()
    grc_provider: GRCProvider = MockGRCProvider()

    if settings.openai_api_key:
        model_client = OpenAIChatCompletionClient(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
        )

        access_request_agent = AccessRequestAgent(
            model_client,
            itsm_provider,
            grc_provider,
            identity_provider=identity_provider,
        )
        access_review_agent = AccessReviewAgent(
            model_client,
            identity_provider,
            grc_provider,
        )
        lifecycle_agent = LifecycleAgent(
            model_client,
            identity_provider,
            itsm_provider,
        )
        monitoring_agent = MonitoringAgent(
            model_client,
            identity_provider,
            siem_provider,
            grc_provider,
        )
        risk_agent = RiskAgent(
            model_client,
            identity_provider,
            grc_provider,
            siem_provider,
        )

        coordinator = CoordinatorAgent(
            model_client,
            access_request_agent,
            access_review_agent,
            lifecycle_agent,
            monitoring_agent,
            risk_agent,
        )

        return DashboardServices(
            settings=settings,
            identity_provider=identity_provider,
            itsm_provider=itsm_provider,
            siem_provider=siem_provider,
            grc_provider=grc_provider,
            coordinator=coordinator,
            mock_mode=False,
            access_request_agent=access_request_agent,
            access_review_agent=access_review_agent,
            lifecycle_agent=lifecycle_agent,
            monitoring_agent=monitoring_agent,
            risk_agent=risk_agent,
            model_client=model_client,
        )

    coordinator = MockCoordinator(
        identity_provider=identity_provider,
        itsm_provider=itsm_provider,
        siem_provider=siem_provider,
        grc_provider=grc_provider,
    )

    return DashboardServices(
        settings=settings,
        identity_provider=identity_provider,
        itsm_provider=itsm_provider,
        siem_provider=siem_provider,
        grc_provider=grc_provider,
        coordinator=coordinator,
        mock_mode=True,
    )
