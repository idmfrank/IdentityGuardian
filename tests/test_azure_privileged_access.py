import sys
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace


class _DummyCredential:  # pragma: no cover - simple shim for imports
    def __init__(self, *args, **kwargs):
        pass

    async def close(self):
        return None


class _DummyAPIVersion:
    BETA = "beta"


class _DummyGraphClient:  # pragma: no cover - stub for dependency
    def __init__(self, *args, **kwargs):
        pass


msgraph_core = SimpleNamespace(APIVersion=_DummyAPIVersion)
msgraph_module = SimpleNamespace(core=msgraph_core, GraphServiceClient=_DummyGraphClient)

sys.modules.setdefault("msgraph", msgraph_module)
sys.modules.setdefault("msgraph.core", msgraph_core)

azure_identity_aio = SimpleNamespace(
    AzureCliCredential=_DummyCredential,
    ManagedIdentityCredential=_DummyCredential,
)

sys.modules.setdefault("azure", SimpleNamespace(identity=SimpleNamespace(aio=azure_identity_aio)))
sys.modules.setdefault("azure.identity", SimpleNamespace(aio=azure_identity_aio))
sys.modules.setdefault("azure.identity.aio", azure_identity_aio)

from identity_guardian.integrations.identity_provider import AzureIdentityProvider


class AzurePrivilegedAccessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.provider = AzureIdentityProvider()
        self.role_config = {
            "role_definition_id": "62e90394-69f5-4237-9190-012177145e10",
            "directory_scope_id": "/",
            "duration": "PT2H",
        }

    def test_build_privileged_role_request_body_defaults(self) -> None:
        body = self.provider._build_privileged_role_request_body(
            "user123",
            "Emergency access",
            self.role_config,
        )

        self.assertEqual(body["principalId"], "user123")
        self.assertEqual(
            body["roleDefinitionId"],
            self.role_config["role_definition_id"],
        )
        self.assertEqual(body["directoryScopeId"], "/")

        schedule = body["scheduleInfo"]
        self.assertIn("startDateTime", schedule)
        start_time = schedule["startDateTime"]
        self.assertTrue(start_time.endswith("Z"))

        converted = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        self.assertEqual(converted.tzinfo, timezone.utc)

        expiration = schedule["expiration"]
        self.assertEqual(expiration["type"], "afterDuration")
        self.assertEqual(expiration["duration"], "PT2H")

    def test_build_privileged_role_request_body_with_overrides(self) -> None:
        overrides = {
            "startDateTime": "2025-11-06T18:00:00Z",
            "expiration": {"type": "afterDuration", "duration": "PT1H"},
        }

        body = self.provider._build_privileged_role_request_body(
            "user456",
            "Planned change window",
            self.role_config,
            schedule_overrides=overrides,
        )

        schedule = body["scheduleInfo"]
        self.assertEqual(schedule["startDateTime"], overrides["startDateTime"])
        self.assertEqual(schedule["expiration"], overrides["expiration"])

    def test_build_privileged_role_request_body_missing_role_definition(self) -> None:
        with self.assertRaises(ValueError):
            self.provider._build_privileged_role_request_body(
                "user789",
                "Invalid config",
                {},
            )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
