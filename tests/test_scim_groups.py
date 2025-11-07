import asyncio
from types import SimpleNamespace
from typing import Any, Dict, List

from identity_guardian.agents.access_request_agent import AccessRequestAgent
from identity_guardian.agents.lifecycle_agent import LifecycleAgent


class _FakeSCIMClient:
    def __init__(self, groups: List[Any] | None = None):
        self.groups_response = SimpleNamespace(resources=groups or [])
        self.updated: List[Dict[str, Any]] = []
        self.created: List[str] = []
        self.last_filter: str | None = None

    async def list_groups(self, filter: str | None = None):
        self.last_filter = filter
        return self.groups_response

    async def create_group(self, display_name: str, members: List[str] | None = None):
        self.created.append(display_name)
        return {"id": "group-123", "displayName": display_name}

    async def update_group_members(self, group_id: str, add=None, remove=None):
        self.updated.append({"group_id": group_id, "add": add, "remove": remove})
        return f"Group {group_id} updated."


def test_handle_request_syncs_scim_group(monkeypatch):
    agent = object.__new__(AccessRequestAgent)
    fake_result = {"status": "pending"}

    async def _fake_process_request(**_kwargs):
        return fake_result

    fake_scim = _FakeSCIMClient()

    monkeypatch.setattr(
        "identity_guardian.agents.access_request_agent.get_scim_outbound",
        lambda: fake_scim,
    )

    agent.process_request = _fake_process_request  # type: ignore[assignment]
    agent.identity_provider = None  # type: ignore[attr-defined]

    async def _scenario():
        return await AccessRequestAgent.handle_request(
            agent,
            {
                "user_id": "user-001",
                "resource_id": "finance_analyst",
                "access_level": "member",
                "business_justification": "Quarter close",
            },
        )

    response = asyncio.run(_scenario())

    assert response["status"] == "pending"
    assert response["group_sync"]["groupId"] == "group-123"
    assert fake_scim.last_filter == 'displayName eq "IG-Finance-Analysts"'
    assert fake_scim.updated[0]["add"] == ["user-001"]


def test_handle_leaver_cleans_groups(monkeypatch):
    lifecycle_agent = object.__new__(LifecycleAgent)
    lifecycle_agent.scim_outbound = _FakeSCIMClient(
        groups=[{"id": "g1", "members": [{"value": "user-xyz"}]}]
    )

    class _FakeProvider:
        def __init__(self):
            self.deprovisioned: List[str] = []

        async def deprovision_user(self, user_id: str):
            self.deprovisioned.append(user_id)

    fake_provider = _FakeProvider()

    async def _fake_get_identity_provider(*_args, **_kwargs):
        return fake_provider

    monkeypatch.setattr(
        "identity_guardian.agents.lifecycle_agent.get_identity_provider",
        _fake_get_identity_provider,
    )

    message = asyncio.run(LifecycleAgent.handle_leaver(lifecycle_agent, "user-xyz"))

    assert fake_provider.deprovisioned == ["user-xyz"]
    assert lifecycle_agent.scim_outbound.updated[0]["remove"] == ["user-xyz"]
    assert "group cleanup" in message
