# Identity Security AI Agent Framework

A Python-based multi-agent framework for identity security automation, built on Microsoft Agent Framework (AutoGen).

## Overview

This framework implements specialized AI agents that handle critical identity security use cases:

- **Access Request Management** - Automated access request processing, approval workflows, and provisioning
- **Access Reviews** - Periodic access certification campaigns with intelligent recommendations
- **Identity Lifecycle Management** - Joiner/mover/leaver workflows with automated provisioning
- **Identity Monitoring** - Anomaly detection, dormant accounts, and security alerting
- **Identity Risk Management** - Risk scoring, compliance checking, and SoD violation detection

## Architecture

The framework uses a multi-agent architecture with specialized agents coordinated by a central orchestrator:

```
┌─────────────────────────────────────────┐
│      Coordinator Agent                  │
│  (Intelligent Request Routing)          │
└──────────────┬──────────────────────────┘
               │
    ┌──────────┴──────────┬───────────────┬───────────────┬──────────────┐
    │                     │               │               │              │
┌───▼────┐        ┌───────▼─────┐  ┌─────▼──────┐  ┌────▼─────┐  ┌────▼─────┐
│ Access │        │   Access    │  │ Lifecycle  │  │ Monitor  │  │   Risk   │
│Request │        │   Review    │  │   Agent    │  │  Agent   │  │  Agent   │
│ Agent  │        │   Agent     │  │            │  │          │  │          │
└────────┘        └─────────────┘  └────────────┘  └──────────┘  └──────────┘
```

## Features

### Core Capabilities

- **Multi-Agent Orchestration** - Powered by Microsoft Agent Framework with intelligent routing
- **AI-Powered Decisions** - LLM-based recommendations for access requests and reviews
- **Mock Integrations** - Simulated identity providers, ITSM, SIEM, and GRC systems
- **Risk-Based Access** - Automated risk scoring and policy compliance checking
- **Telemetry & Observability** - OpenTelemetry integration for agent tracking
- **CLI Interface** - Rich terminal interface for testing workflows

### Specialized Agents

1. **Access Request Agent**
   - Process access requests with validation
   - Assess risk and check policy compliance
   - Route to appropriate approvers
   - Automate provisioning

2. **Access Review Agent**
   - Generate review campaigns
   - Provide AI-powered recommendations
   - Track completion rates
   - Automate access revocation

3. **Lifecycle Agent**
   - Joiner: New hire provisioning
   - Mover: Role change workflows
   - Leaver: Offboarding and deprovisioning

4. **Monitoring Agent**
   - Detect behavioral anomalies
   - Find dormant and orphaned accounts
   - Monitor privilege escalations
   - Generate security alerts

5. **Risk Agent**
   - Calculate comprehensive risk scores
   - Detect SoD violations
   - Generate compliance reports
   - Recommend remediation steps

## Installation

### Prerequisites

- Python 3.11+
- OpenAI API key (for AI features)

### Setup

1. Clone or download the project

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

4. Run the CLI:
```bash
python main.py
```

## Configuration

Edit `.env` file to configure:

```env
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o

LOG_LEVEL=INFO
FRAMEWORK_ENV=development

IDENTITY_PROVIDER=mock
ITSM_PROVIDER=mock
SIEM_PROVIDER=mock
GRC_PROVIDER=mock
```

## Usage

### CLI Commands

The framework provides an interactive CLI with demo workflows:

1. **Demo Access Request** - Submit and process an access request
2. **Demo Review Campaign** - Create an access review campaign
3. **Demo Joiner** - Process new hire onboarding
4. **Demo Risk Assessment** - Calculate user risk score
5. **Demo Monitoring** - Analyze user behavior
6. **Metrics** - View agent activity metrics

### Example: Access Request Workflow

```python
from identity_security_framework.agents.coordinator import CoordinatorAgent

result = await coordinator.process_request("access_request", {
    "user_id": "user001",
    "resource_id": "financial_db",
    "resource_type": "database",
    "access_level": "read",
    "business_justification": "Quarterly reporting"
})
```

### Example: Risk Assessment

```python
result = await coordinator.process_request("calculate_risk", {
    "user_id": "user001"
})

print(f"Risk Score: {result['risk_score']}")
print(f"Risk Level: {result['risk_level']}")
```

## Project Structure

```
identity_security_framework/
├── agents/                    # AI agent implementations
│   ├── access_request_agent.py
│   ├── access_review_agent.py
│   ├── lifecycle_agent.py
│   ├── monitoring_agent.py
│   ├── risk_agent.py
│   └── coordinator.py
├── config/                    # Configuration management
│   └── settings.py
├── integrations/              # Mock system integrations
│   ├── identity_provider.py
│   ├── itsm.py
│   ├── siem.py
│   └── grc.py
├── models/                    # Data models
│   └── identity.py
├── utils/                     # Utilities
│   └── telemetry.py
└── cli.py                     # CLI interface
```

## Next Steps

### Phase 2 Enhancements

- Real Azure AD/Entra ID integration
- SCIM 2.0 connector framework
- Slack/Teams integration for approvals
- Web dashboard for monitoring
- PostgreSQL for audit trails
- ML-based risk scoring models
- Production SIEM integrations
- GRC platform connectors
- Comprehensive API layer

## Technology Stack

- **Microsoft Agent Framework** (AutoGen) - Multi-agent orchestration
- **OpenAI GPT-4** - AI-powered decision making
- **Pydantic** - Data validation
- **Rich** - Terminal UI
- **OpenTelemetry** - Observability

## License

MIT License

## Contributing

This is a demonstration framework for identity security automation. For production use, integrate with real identity providers, SIEM, and GRC systems.
