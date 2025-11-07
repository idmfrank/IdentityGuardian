import asyncio
from datetime import datetime
from types import SimpleNamespace

from backend.api import access, groups, lifecycle, monitoring, reviews, risk, scim
from backend.main import _initial_data
from backend.services import init_services


class ModelStub(dict):
    def __getattr__(self, item):  # pragma: no cover - simple attr access
        return self[item]

    def model_dump(self, by_alias: bool = False):  # pragma: no cover - matches pydantic API
        return dict(self)


def build_context():
    services = asyncio.run(init_services())
    data = _initial_data(services)
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(services=services, data=data)))
    return services, data, request


def test_access_request_flow():
    services, data, request = build_context()
    payload = ModelStub(
        user_id="user001",
        resource="snowflake_prod",
        resource_id="snowflake_prod",
        access_level="read",
        business_justification="Quarterly reporting",
        justification="Quarterly reporting",
        resource_type="application",
    )
    record = asyncio.run(access.submit_request(payload, request, services))
    assert record.status in {"pending", "pending_approval"}
    assert record.user_id == "user001"

    requests = asyncio.run(access.list_requests(request))
    assert any(item.request_id == record.request_id for item in requests)


def test_review_campaign_and_decision():
    services, data, request = build_context()
    payload = ModelStub(campaign_name="Quarterly", scope="All", duration_days=10)
    campaign = asyncio.run(reviews.create_campaign(payload, request, services))
    assert campaign.review_items

    first_item = campaign.review_items[0]
    decision_payload = ModelStub(decision="approved", reviewer_id="mgr001")
    updated_item = asyncio.run(
        reviews.submit_review_decision(
            campaign.campaign_id,
            first_item.review_item_id,
            decision_payload,
            request,
            services,
        )
    )
    assert updated_item.status in {"approved", "pending", "revoked", "modified"}


def test_lifecycle_endpoints():
    services, data, request = build_context()
    joiner_payload = ModelStub(
        user_id="user777",
        username="casey.new",
        email="casey.new@example.com",
        first_name="Casey",
        last_name="New",
        department="Engineering",
        manager_id="mgr100",
        roles=["Developer"],
        start_date=datetime.utcnow(),
    )
    event = asyncio.run(lifecycle.process_joiner(joiner_payload, request, services))
    assert event.event_type == "joiner"

    events = asyncio.run(lifecycle.list_events(request))
    assert any(item.event_id == event.event_id for item in events)


def test_monitoring_and_risk_routes():
    services, data, request = build_context()
    behavior = asyncio.run(
        monitoring.analyze_user_behavior(
            ModelStub(user_id="user001"),
            request,
            services,
        )
    )
    assert behavior.user_id == "user001"

    alerts = asyncio.run(monitoring.list_alerts(request))
    assert len(alerts) >= 1

    dormant = asyncio.run(monitoring.detect_dormant_accounts(request, services))
    assert dormant.accounts is not None

    risk_record = asyncio.run(risk.calculate_risk(ModelStub(user_id="user001"), request, services))
    assert 0.0 <= risk_record.risk_score <= 1.0

    block = asyncio.run(risk.auto_block(ModelStub(user_id="user001", reason="High risk"), request, services))
    assert "Mock Conditional Access" in block.message


def test_scim_and_groups_management():
    services, data, request = build_context()

    outbound_event = asyncio.run(
        scim.record_outbound(
            ModelStub(payload={"op": "add"}, status="success", detail=None),
            request,
        )
    )
    assert outbound_event.direction == "outbound"

    inbound_event = asyncio.run(
        scim.record_inbound(
            ModelStub(payload={"op": "patch"}, status="success", detail=None),
            request,
        )
    )
    assert inbound_event.direction == "inbound"

    outbound_logs = asyncio.run(scim.list_outbound_logs(request))
    inbound_logs = asyncio.run(scim.list_inbound_logs(request))
    assert len(outbound_logs) == 1 and len(inbound_logs) == 1

    group = asyncio.run(
        groups.create_group(
            ModelStub(display_name="Blue Team", role="blue_team"),
            request,
            services,
        )
    )
    assert group.display_name == "Blue Team"

    updated = asyncio.run(
        groups.add_members(
            group.group_id,
            ModelStub(members=["user001", "user002"]),
            request,
        )
    )
    assert "user001" in updated.members

    trimmed = asyncio.run(groups.remove_member(group.group_id, "user001", request))
    assert "user001" not in trimmed.members
