# IdentityGuardian

## Project Overview

A Python-based multi-agent framework for identity security automation using Microsoft Agent Framework (AutoGen). The system implements specialized AI agents for handling access requests, access reviews, identity lifecycle management, security monitoring, and risk management.

## Architecture

### Multi-Agent System
- **Coordinator Agent**: Routes requests to specialized agents
- **Access Request Agent**: Handles access request workflows and approvals
- **Access Review Agent**: Manages periodic access certification campaigns
- **Lifecycle Agent**: Processes joiner/mover/leaver events
- **Monitoring Agent**: Detects anomalies and security threats
- **Risk Agent**: Calculates risk scores and compliance status

### Technology Stack
- Microsoft Agent Framework (AutoGen) for multi-agent orchestration
- OpenAI GPT-4 for AI-powered decision making
- Pydantic for data validation and settings
- Rich for CLI interface
- OpenTelemetry for observability

## Project Structure

```
identity_guardian/
├── agents/           - AI agent implementations
├── config/           - Configuration and settings
├── integrations/     - Mock system integrations (IdP, ITSM, SIEM, GRC)
├── models/           - Data models for identity entities
├── utils/            - Utilities and telemetry
└── cli.py            - CLI interface
```

## Recent Changes

### 2025-11-06: Initial Framework Implementation
- Created multi-agent architecture with 5 specialized agents
- Implemented coordinator for intelligent request routing
- Built mock integrations for identity providers, ITSM, SIEM, and GRC
- Added CLI interface with demo workflows
- Configured OpenTelemetry for agent metrics
- Set up Pydantic-based configuration management

## Configuration

### Environment Variables
- `OPENAI_API_KEY`: Required for AI features
- `OPENAI_MODEL`: Model to use (default: gpt-4o)
- `LOG_LEVEL`: Logging level (INFO, DEBUG, etc.)
- `FRAMEWORK_ENV`: Environment (development, staging, production)

### Setup
1. Copy `.env.example` to `.env`
2. Add your OpenAI API key
3. Run `python main.py`

## Use Cases

1. **Access Request Management**: Automated processing of access requests with risk assessment
2. **Access Reviews**: Periodic certification campaigns with AI recommendations
3. **Identity Lifecycle**: Joiner/mover/leaver workflows with provisioning automation
4. **Security Monitoring**: Anomaly detection and alerting
5. **Risk Management**: Risk scoring and compliance reporting

## User Preferences

None configured yet.

## Next Phase Features

- Azure AD/Entra ID integration
- SCIM 2.0 connectors
- Slack/Teams notifications
- Web dashboard
- PostgreSQL audit trails
- Production SIEM integrations
- ML-based risk models
