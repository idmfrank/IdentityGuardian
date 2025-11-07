# IdentityGuardian

A Python-based multi-agent framework for identity security automation, built on the Microsoft Agent Framework (AutoGen).

## Overview

IdentityGuardian ships with specialized AI agents that work together to cover critical identity security use cases.  The framework can run entirely in mock mode (no API keys required) or leverage OpenAI-powered reasoning for richer recommendations.

Key capabilities include:

- **Access Request Management** - Automated access request processing, approval workflows, Teams-based approvals, and provisioning
- **Access Reviews** - Periodic access certification campaigns with intelligent recommendations
- **Identity Lifecycle Management** - Joiner/mover/leaver workflows with automated provisioning
- **Identity Monitoring** - Anomaly detection, Sentinel-driven insights, dormant accounts, and security alerting
- **Identity Risk Management** - Risk scoring, compliance checking, and SoD violation detection
- **Auto-Block on High Risk** - Clone a Conditional Access block policy, target the risky user, and notify SecOps when the risk threshold is exceeded

## Architecture

The framework uses a multi-agent architecture with specialized agents coordinated by a central orchestrator.  When no OpenAI credentials are configured the CLI automatically falls back to a mock coordinator so all workflows remain available.

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

- **Multi-Agent Orchestration** – Powered by Microsoft Agent Framework with intelligent routing across specialized agents
- **AI-Powered Decisions** – LLM-based recommendations for access requests, reviews, lifecycle events, and risk assessments
- **Dual-Mode Operation** – Mock coordinator for deterministic demos plus full OpenAI integrations when an API key is supplied
- **Mock Integrations** – Simulated identity provider, ITSM, SIEM, and GRC systems for local development
- **Risk-Based Access** – Automated risk scoring, policy compliance checks, and SoD violation detection
- **Telemetry Utilities** – OpenTelemetry helpers and built-in agent metrics for tracking activity
- **CLI Interface** – Rich terminal experience for exploring end-to-end workflows

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
   - Ticket creation and baseline access provisioning

4. **Monitoring Agent**
   - Detect behavioral anomalies
   - Find dormant and orphaned accounts
   - Monitor privilege escalations
   - Generate security alerts
   - Auto-block high-risk identities based on Sentinel correlations

5. **Risk Agent**
   - Calculate comprehensive risk scores
   - Detect SoD violations
   - Generate compliance reports
   - Recommend remediation steps
   - Log compliance events to the mock GRC provider

## Installation

### Prerequisites

- Python 3.11+
- OpenAI API key (optional - for AI-powered features)

### Setup

1. Clone or download the project

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables (optional):
```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY for AI features
```

4. Run the CLI:
```bash
python main.py
```

### Mock Mode vs AI Mode

The framework supports two operating modes:

**Mock Mode** (No API Key Required)
- Runs deterministic workflows without external API calls via `MockCoordinator`
- Perfect for testing, demos, and understanding the framework
- All core workflows are fully functional using simulated data
- Uses rule-based decision making and mock integrations

**AI Mode** (Requires OpenAI API Key)
- Uses GPT-4 class models for intelligent recommendations and decisions
- Provides natural language insights and analysis
- Adaptive risk scoring and anomaly detection across agents
- Set `OPENAI_API_KEY` in `.env` to enable

## Configuration

Edit `.env` file to configure:

```env
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o

# Optional Azure OpenAI configuration
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_DEPLOYMENT=

LOG_LEVEL=INFO
FRAMEWORK_ENV=development

# Identity and integration providers
IDENTITY_PROVIDER=mock
ITSM_PROVIDER=mock
SIEM_PROVIDER=mock
GRC_PROVIDER=mock

# Microsoft Teams approval bot (optional)
BOT_ID=
BOT_PASSWORD=
TEAMS_CHANNEL_ID=
TEAMS_ALERT_CHANNEL_ID=

# Auto-block configuration
AUTO_BLOCK_THRESHOLD=90
CA_BLOCK_POLICY_ID=
INVESTIGATION_CHANNEL_ID=

# Microsoft Sentinel monitoring (optional)
SENTINEL_WORKSPACE_ID=

# Optional Microsoft Entra ID configuration
AZURE_TENANT_ID=your-tenant-id
AZURE_SUBSCRIPTION_ID=your-sub-id
```

### SCIM 2.0 Integration

IdentityGuardian provides both outbound (source) and inbound (target) SCIM 2.0 support for joiner/mover/leaver automation.

1. **Configure environment variables** – update `.env` with the SCIM bearer token, base URL for your target, and inbound server host/port values. Sample entries are included in `.env.example`.
2. **Run the inbound server (optional)** – expose `/scim/v2/Users` and `/scim/v2/Groups` endpoints via:

   ```bash
   python -c "from identity_guardian.integrations.scim import get_scim_inbound; get_scim_inbound().run()"
   ```

   Pair this with a tunneling service such as `ngrok http 8080` when testing with SaaS identity sources like Entra ID or SailPoint.
3. **Trigger outbound provisioning** – once configured, lifecycle flows automatically push SCIM changes. You can also run the demo script:

   ```bash
   python examples/scim_demo.py
   ```

   The script exercises joiner, mover, and leaver operations via the outbound client and prints the SCIM responses.

### Conditional Access Auto-Block

IdentityGuardian prefers Conditional Access (CA) enforcement to hard disabling an account. Cloning a pre-approved CA template keeps sign-in, multi-factor authentication, and device policies intact while blocking all access paths for the targeted identity. It also leaves the account enabled so that password resets and self-service remediation continue to work during an investigation.

| Feature | `accountEnabled = false` | Conditional Access Block |
| --- | --- | --- |
| Immediate block | ✅ | ✅ |
| Detailed audit trail | ✅ | ✅ |
| User can reset password | ❌ | ✅ |
| Reversible without downtime | ❌ | ✅ |
| Works with MFA, device conditions, etc. | ❌ | ✅ |
| Recommended approach | ❌ | ✅ |

To enable the workflow:

1. Create a **template** CA policy that blocks all apps and is kept disabled (for example `TEMPLATE - High Risk Block`).
2. Copy the policy ID and set `CA_BLOCK_POLICY_ID` in `.env`.
3. Provide a SecOps collaboration space (Teams channel, etc.) and set `INVESTIGATION_CHANNEL_ID`.

When the risk agent detects a score above `AUTO_BLOCK_THRESHOLD`, it clones the template policy, scopes it to the impacted user, enables it, and posts an investigation card to the SecOps channel. Analysts can select **Re-enable User** directly from the card, which deletes the cloned CA policy and notifies the alert channel that access has been restored.

Run the demo locally to observe the flow:

```bash
python examples/auto_block_demo.py
```

You will see the risk agent report a `ca_blocked` action in the console; when the webhook receives a re-enable action it removes the policy and broadcasts a restoration alert.

### Privileged Identity Management (PIM) Configuration

IdentityGuardian can submit JIT privileged access requests through Microsoft Graph when `IDENTITY_PROVIDER=azure`. Privileged resources are mapped in `identity_guardian/config/settings.py` via `PRIVILEGED_RESOURCE_ROLE_MAP`. The project ships with a predefined entry for the Microsoft Entra **Global Administrator** role (role definition ID `62e90394-69f5-4237-9190-012177145e10`). Update or extend this mapping with the role definition IDs for the privileged roles you intend to manage.

> **Important:** The application identity used by IdentityGuardian must be granted the `PrivilegedAccess.ReadWrite.AzureAD` permission to create PIM role assignment requests.

## Usage

### CLI Commands

The framework provides an interactive CLI with demo workflows:

1. **Demo Access Request** – Submit and process an access request
2. **Demo Review Campaign** – Create an access review campaign
3. **Demo Joiner** – Process new hire onboarding
4. **Demo Risk Assessment** – Calculate user risk score
5. **Demo Monitoring** – Analyze user behavior
6. **Metrics** – View agent activity metrics and recent events
7. **Exit** – Quit the CLI

### Example: Access Request Workflow

```python
from identity_guardian.agents.coordinator import CoordinatorAgent

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

### Microsoft Teams Approval Bot

IdentityGuardian can automatically post adaptive approval cards to Microsoft Teams and activate Privileged Identity Management (PIM) assignments when approvers click **Approve**. To enable the bot:

1. Register a bot in Azure (App Registrations) using redirect URI `https://token.botframework.com/.auth/web/redirect`.
2. Grant the bot `ChannelMessage.Send` and `TeamsActivity.Send` application permissions and create a client secret.
3. Populate `BOT_ID`, `BOT_PASSWORD`, and `TEAMS_CHANNEL_ID` in `.env`.
4. Start the webhook receiver so Teams can deliver action callbacks:

```bash
uvicorn webhook:app --reload --port 8000
```

5. Expose the webhook (for example with `ngrok http 8000`) and set the Bot Framework messaging endpoint accordingly.

Once configured, approving a PIM request from Teams will automatically activate the role assignment.

### Microsoft Sentinel Monitoring

The monitoring agent can run Microsoft Sentinel Kusto queries to incorporate risky sign-ins and privilege escalations into user risk scores. Provide your Sentinel workspace ID in `.env` and sign in with Azure CLI credentials (`az login`) prior to running the CLI. The agent consumes the following data:

- Risky sign-ins over the past 24 hours
- Privilege escalation audit events over the past 24 hours

When risky sign-ins overlap with privilege escalations, the monitoring agent will call the auto-block workflow to disable the account and post a Teams alert. The Sentinel results are folded into the overall risk score that the Risk Agent returns.

### Example Scripts

For additional end-to-end scenarios, review and run `examples/example_usage.py` and the high-risk auto-block demo below.

### Auto-Block Demo

```bash
python examples/auto_block_demo.py
```

The demo uses mock integrations but exercises the full workflow: calculating the combined Entra + Sentinel score, disabling the identity, and emitting a Teams alert payload.

To continuously poll Sentinel for correlated events, run the scheduler:

```bash
python scheduler.py
```

## Testing

Run the unit test suite from the repository root:

```bash
python -m unittest discover -s tests
```

## Project Structure

```
identity_guardian/
├── agents/                     # AI agent implementations
│   ├── access_request_agent.py
│   ├── access_review_agent.py
│   ├── lifecycle_agent.py
│   ├── monitoring_agent.py
│   ├── risk_agent.py
│   ├── coordinator.py
│   └── mock_coordinator.py
├── cli.py                      # Interactive CLI
├── config/
│   └── settings.py             # Pydantic settings & Graph helpers
├── integrations/
│   ├── identity_provider.py    # Mock & Azure identity provider
│   ├── itsm.py                 # Mock ITSM adapter
│   ├── siem.py                 # Mock SIEM adapter
│   └── grc.py                  # Mock GRC adapter
├── models/
│   └── identity.py             # Core Pydantic models
├── utils/
│   └── telemetry.py            # Logging & telemetry utilities
├── examples/
│   ├── example_usage.py        # Scripted agent demos
│   └── auto_block_demo.py      # High-risk auto-block demonstration
└── __init__.py

scheduler.py                    # Optional Sentinel watcher loop
```

## Next Steps

### Phase 2 Enhancements

- Harden Azure AD/Entra ID integration for production tenants
- SCIM 2.0 connector framework
- Slack/Teams integration for approvals
- Web dashboard for monitoring
- PostgreSQL or other persistent audit trail storage
- ML-based risk scoring models
- Production SIEM integrations (Splunk, Sentinel, etc.)
- GRC platform connectors
- Comprehensive API layer

## Technology Stack

- **Microsoft Agent Framework (AutoGen)** – Multi-agent orchestration
- **OpenAI GPT-4 class models** – AI-powered decision making
- **Pydantic & pydantic-settings** – Configuration and data validation
- **Rich** – Terminal UI
- **OpenTelemetry** – Observability helpers
- **Azure Identity & Microsoft Graph SDK** – Optional Entra ID integration

## License

MIT License

## Contributing

This is a demonstration framework for identity security automation. For production use, integrate with real identity providers, SIEM, and GRC systems.
