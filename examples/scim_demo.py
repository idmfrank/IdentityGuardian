"""Demonstrate outbound SCIM provisioning using IdentityGuardian helpers."""

import asyncio

from identity_guardian.integrations.identity_provider import get_identity_provider
from identity_guardian.integrations.scim import get_scim_outbound


async def main() -> None:
    provider = await get_identity_provider()

    try:
        scim_client = get_scim_outbound()
    except ValueError as exc:
        print(f"SCIM outbound client not configured: {exc}")
        return

    user_payload = {
        "userPrincipalName": "newuser@contoso.com",
        "givenName": "New",
        "surname": "User",
        "active": True,
    }

    print("\n--- Joiner workflow ---")
    await provider.request_access(
        user_payload["userPrincipalName"],
        "baseline_access",
        "SCIM demo joiner",
    )
    joiner_status = await scim_client.provision_user(user_payload)
    print(joiner_status)

    print("\n--- Mover workflow ---")
    mover_status = await scim_client.update_user(user_payload["userPrincipalName"], user_payload)
    print(mover_status)

    print("\n--- Leaver workflow ---")
    await provider.deprovision_user(user_payload["userPrincipalName"])
    leaver_status = await scim_client.deprovision_user(user_payload["userPrincipalName"])
    print(leaver_status)


if __name__ == "__main__":
    asyncio.run(main())
