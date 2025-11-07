from identity_guardian.integrations.scim import (
    service_provider_config_payload,
    well_known_scim_payload,
)


def test_service_provider_config():
    data = service_provider_config_payload()
    assert data["patch"]["supported"] is True
    assert any(scheme["name"] == "Bearer Token" for scheme in data["authenticationSchemes"])


def test_well_known_scim():
    data = well_known_scim_payload()
    assert data["schemas"] == ["urn:ietf:params:scim:api:messages:2.0:Discovery"]
    assert any("Bearer Token" == scheme["name"] for scheme in data["authenticationSchemes"])
