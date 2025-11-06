#!/usr/bin/env python3
"""
Example usage of the IdentityGuardian
Demonstrates various agent capabilities
"""

import asyncio
from datetime import datetime
from identity_guardian.config.settings import get_settings
from identity_guardian.agents.coordinator import CoordinatorAgent
from identity_guardian.agents.access_request_agent import AccessRequestAgent
from identity_guardian.agents.access_review_agent import AccessReviewAgent
from identity_guardian.agents.lifecycle_agent import LifecycleAgent
from identity_guardian.agents.monitoring_agent import MonitoringAgent
from identity_guardian.agents.risk_agent import RiskAgent
from identity_guardian.integrations.identity_provider import MockIdentityProvider
from identity_guardian.integrations.itsm import MockITSMProvider
from identity_guardian.integrations.siem import MockSIEMProvider
from identity_guardian.integrations.grc import MockGRCProvider
from identity_guardian.models.identity import User, UserStatus
from autogen_ext.models.openai import OpenAIChatCompletionClient


async def example_access_request():
    """Example: Process an access request"""
    print("\n=== Access Request Example ===")
    
    settings = get_settings()
    if not settings.openai_api_key:
        print("Error: OPENAI_API_KEY not set")
        return
    
    model_client = OpenAIChatCompletionClient(
        model=settings.openai_model,
        api_key=settings.openai_api_key
    )
    
    identity_provider = MockIdentityProvider()
    itsm_provider = MockITSMProvider()
    grc_provider = MockGRCProvider()
    
    agent = AccessRequestAgent(model_client, identity_provider, itsm_provider, grc_provider)
    
    result = await agent.process_request(
        user_id="user001",
        resource_id="production_database",
        resource_type="database",
        access_level="admin",
        business_justification="Need to perform emergency maintenance"
    )
    
    print(f"Request ID: {result['request_id']}")
    print(f"Status: {result['status']}")
    print(f"Risk Score: {result['risk_score']:.2f}")
    print(f"Approvers: {', '.join(result['approvers'])}")
    print(f"Recommendation: {result['recommendation']}")


async def example_access_review():
    """Example: Create access review campaign"""
    print("\n=== Access Review Campaign Example ===")
    
    settings = get_settings()
    if not settings.openai_api_key:
        print("Error: OPENAI_API_KEY not set")
        return
    
    model_client = OpenAIChatCompletionClient(
        model=settings.openai_model,
        api_key=settings.openai_api_key
    )
    
    identity_provider = MockIdentityProvider()
    grc_provider = MockGRCProvider()
    
    agent = AccessReviewAgent(model_client, identity_provider, grc_provider)
    
    result = await agent.create_campaign(
        campaign_name="Quarterly Access Review - Q4 2025",
        scope="All Active Users",
        duration_days=30
    )
    
    print(f"Campaign ID: {result['campaign_id']}")
    print(f"Campaign Name: {result['campaign_name']}")
    print(f"Review Items: {result['review_items_count']}")
    print(f"Start: {result['start_date']}")
    print(f"End: {result['end_date']}")


async def example_joiner():
    """Example: Process new hire"""
    print("\n=== New Hire Onboarding Example ===")
    
    settings = get_settings()
    if not settings.openai_api_key:
        print("Error: OPENAI_API_KEY not set")
        return
    
    model_client = OpenAIChatCompletionClient(
        model=settings.openai_model,
        api_key=settings.openai_api_key
    )
    
    identity_provider = MockIdentityProvider()
    itsm_provider = MockITSMProvider()
    
    agent = LifecycleAgent(model_client, identity_provider, itsm_provider)
    
    new_user = User(
        user_id="user100",
        username="charlie.brown",
        email="charlie.brown@company.com",
        first_name="Charlie",
        last_name="Brown",
        department="Engineering",
        manager_id="mgr001",
        status=UserStatus.ACTIVE,
        hire_date=datetime.now(),
        roles=["Software Engineer"]
    )
    
    result = await agent.process_joiner(new_user, datetime.now())
    
    print(f"Event ID: {result['event_id']}")
    print(f"User: {result['user_id']}")
    print(f"Status: {result['status']}")
    print(f"\nProvisioning Tasks:")
    for task in result['provisioning_tasks']:
        print(f"  - {task}")


async def example_risk_assessment():
    """Example: Calculate user risk score"""
    print("\n=== Risk Assessment Example ===")
    
    settings = get_settings()
    if not settings.openai_api_key:
        print("Error: OPENAI_API_KEY not set")
        return
    
    model_client = OpenAIChatCompletionClient(
        model=settings.openai_model,
        api_key=settings.openai_api_key
    )
    
    identity_provider = MockIdentityProvider()
    grc_provider = MockGRCProvider()
    siem_provider = MockSIEMProvider()
    
    agent = RiskAgent(model_client, identity_provider, grc_provider, siem_provider)
    
    result = await agent.calculate_user_risk_score("user001")
    
    print(f"User: {result['user_id']}")
    print(f"Risk Score: {result['risk_score']}")
    print(f"Risk Level: {result['risk_level']}")
    print(f"\nRisk Factors:")
    for factor in result['risk_factors']:
        print(f"  - [{factor['severity']}] {factor['description']}")
    print(f"\nRemediation Steps:")
    for step in result['remediation_steps']:
        print(f"  - {step}")


async def example_monitoring():
    """Example: Analyze user behavior"""
    print("\n=== Behavior Monitoring Example ===")
    
    settings = get_settings()
    if not settings.openai_api_key:
        print("Error: OPENAI_API_KEY not set")
        return
    
    model_client = OpenAIChatCompletionClient(
        model=settings.openai_model,
        api_key=settings.openai_api_key
    )
    
    identity_provider = MockIdentityProvider()
    siem_provider = MockSIEMProvider()
    
    agent = MonitoringAgent(model_client, identity_provider, siem_provider)
    
    result = await agent.analyze_user_behavior("user001")
    
    print(f"User: {result['user_id']}")
    print(f"Anomalies Detected: {result.get('anomalies_detected', 0)}")
    
    if result.get('anomalies_detected', 0) > 0:
        print(f"Alert ID: {result['alert_id']}")
        print(f"Risk Level: {result['risk_level']}")
        print(f"\nAnomalies:")
        for anomaly in result['anomalies']:
            print(f"  - [{anomaly['severity']}] {anomaly['description']}")


async def main():
    """Run all examples"""
    print("IdentityGuardian - Example Usage")
    print("=" * 50)
    
    try:
        await example_access_request()
        await asyncio.sleep(1)
        
        await example_access_review()
        await asyncio.sleep(1)
        
        await example_joiner()
        await asyncio.sleep(1)
        
        await example_risk_assessment()
        await asyncio.sleep(1)
        
        await example_monitoring()
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
