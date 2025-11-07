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

## Web Dashboard

IdentityGuardian also ships with a production-ready web dashboard that exposes the same core identity security workflows over a modern web stack.  The dashboard is split into a FastAPI backend and a React + Vite frontend, styled with Tailwind CSS, wired together with Zustand for state management, and visualized with Recharts.

### Technology Stack

- **Backend API** – FastAPI with Pydantic request models, modular routers, and CORS support for the SPA.
- **Frontend** – React (TypeScript) running on Vite for instant HMR.
- **Styling** – Tailwind CSS utility classes for consistent theming.
- **State** – Lightweight global state via Zustand stores.
- **Charts** – Recharts components for request trends, risk distribution, and monitoring metrics.

### Project Structure

```
IdentityGuardian/
├── backend/                  # FastAPI
│   ├── main.py
│   ├── api/
│   │   ├── access.py
│   │   ├── lifecycle.py
│   │   ├── risk.py
│   │   ├── monitoring.py
│   │   ├── scim.py
│   │   └── groups.py
│   └── models.py
├── frontend/                 # React + Vite
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   └── store/
│   └── vite.config.ts
└── docker-compose.yml
```

### Backend (FastAPI)

`backend/main.py` wires the modular routers and enables the SPA to call the API securely:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api import access, lifecycle, risk, monitoring, scim, groups

app = FastAPI(title="IdentityGuardian Dashboard")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(access.router, prefix="/api/access")
app.include_router(lifecycle.router, prefix="/api/lifecycle")
app.include_router(risk.router, prefix="/api/risk")
app.include_router(monitoring.router, prefix="/api/monitoring")
app.include_router(scim.router, prefix="/api/scim")
app.include_router(groups.router, prefix="/api/groups")


@app.get("/")
def root():
    return {"message": "IdentityGuardian API"}
```

Routers encapsulate domain logic.  For example, `backend/api/access.py` orchestrates access requests through the AccessRequestAgent:

```python
from fastapi import APIRouter
from pydantic import BaseModel
from agents.access_request_agent import AccessRequestAgent

router = APIRouter()
agent = AccessRequestAgent()


class AccessRequest(BaseModel):
    user_id: str
    resource: str
    justification: str


@router.post("/request")
async def submit_request(req: AccessRequest):
    result = await agent.handle_request(req.dict())
    return result


@router.get("/requests")
async def list_requests():
    return [
        {"id": "1", "user": "alice@contoso.com", "resource": "Snowflake", "status": "Approved", "risk": 6}
    ]
```

### Frontend (React + Vite + Tailwind)

The SPA bootstraps from `frontend/src/main.tsx` and renders the router described in `frontend/src/App.tsx`.  Pages live in `frontend/src/pages` and leverage shared components, Zustand stores, and Tailwind utility classes for consistent styling.

The access request page combines form handling with charts:

```tsx
const mockHistory = [
  { date: 'Mon', requests: 12 },
  { date: 'Tue', requests: 19 },
  { date: 'Wed', requests: 15 },
]

export default function AccessRequest() {
  const { register, handleSubmit, reset } = useForm()
  const [status, setStatus] = useState<string | null>(null)

  const onSubmit = async (data: any) => {
    const res = await fetch('http://localhost:8000/api/access/request', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
    const result = await res.json()
    setStatus(`Request submitted: ${result.pim_result}`)
    reset()
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {/* Form */}
      {/* Trend chart rendered via <ResponsiveContainer> */}
    </div>
  )
}
```

Risk insights are rendered with Recharts pie charts, and lifecycle, monitoring, SCIM, and group management pages expose quick actions for each domain.

### Feature Coverage

| Feature        | URL              | Function                            |
| -------------- | ---------------- | ----------------------------------- |
| Access Request | `/access-request` | Submit access requests and track status |
| Access Reviews | `/reviews`        | Start and certify campaigns        |
| Lifecycle      | `/lifecycle`      | Joiner, mover, and leaver workflows |
| Monitoring     | `/monitoring`     | Sentinel alerts and anomaly feeds  |
| Risk           | `/risk`           | Risk scores and automated blocking |
| SCIM Logs      | `/scim`           | Inbound/outbound SCIM visibility    |
| Groups         | `/groups`         | Manage groups and membership        |

### Local Development

Run the dashboard locally with Docker Compose (requires Docker Desktop):

```bash
docker-compose up --build
```

- Backend – available at `http://localhost:8000`.
- Frontend – available at `http://localhost:5173`.
- Environment variables such as `IDENTITY_PROVIDER=azure` and `AZURE_TENANT_ID` can be set in `.env` and consumed by `docker-compose`.

To develop each service independently:

```bash
# Backend API
uvicorn backend.main:app --reload --port 8000

# Frontend SPA
cd frontend
npm install
npm run dev
```

The frontend proxies API calls to `http://localhost:8000/api/*` so that joiner/mover/leaver lifecycle flows, SCIM operations, access requests, and Sentinel risk monitoring are immediately available once both services are running.

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

IdentityGuardian now offers end-to-end SCIM 2.0 group provisioning alongside existing user automation. Outbound flows push groups and memberships to SaaS targets while the inbound FastAPI server receives group CRUD requests from platforms like Microsoft Entra ID or SailPoint.

1. **Configure environment variables** – update `.env` with the SCIM bearer token, base URL for your target, and inbound server host/port values. The new `ROLE_TO_GROUP_MAP` and `SCIM_GROUP_PREFIX` settings in `config/settings.py` drive automatic role-to-group mappings for Access Request Agent workflows.
2. **Run the inbound server (optional)** – expose `/scim/v2/Users` and `/scim/v2/Groups` endpoints via:

   ```bash
   python -c "from identity_guardian.integrations.scim import get_scim_inbound; get_scim_inbound().run()"
   ```

   Pair this with a tunneling service such as `ngrok http 8080` when testing with SaaS identity sources like Entra ID or SailPoint. Group create, patch, delete, and list operations are enforced with bearer token validation and call into the Microsoft Graph provider.
3. **Trigger outbound provisioning** – once configured, lifecycle flows and access approvals automatically push SCIM user and group changes. Demo scripts:

   ```bash
   python examples/scim_demo.py          # Joiner / mover / leaver user flows
   python examples/group_demo.py         # Group CRUD + membership updates
   ```

   The group demo creates a prefixed SCIM group, adds members, and patches membership via the outbound client.

#### Feature Matrix

| Operation | Outbound (Source) | Inbound (Target) |
| --- | --- | --- |
| Create Group | ✅ | ✅ |
| Add/Remove Members | ✅ | ✅ |
| Delete Group | ✅ | ✅ |
| Auto-sync on Access Request | ✅ | — |
| Cleanup on Leaver | ✅ | — |

#### Quick Tests

Create a group via the inbound endpoint (requires the inbound server to be running):

```bash
curl -X POST http://localhost:8080/scim/v2/Groups \
  -H "Authorization: Bearer $SCIM_TARGET_BEARER_TOKEN" \
  -H "Content-Type: application/scim+json" \
  -d '{
    "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"],
    "displayName": "IG-Finance-Analysts"
  }'
```

Exercise outbound group creation and membership updates:

```bash
python examples/group_demo.py
```

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
