"""Demonstrate SCIM group provisioning using the outbound client."""
import asyncio
from typing import Any

from identity_guardian.integrations.scim import get_scim_outbound


async def main() -> None:
    try:
        scim = get_scim_outbound()
    except ValueError as exc:
        print(f"[WARN] SCIM outbound disabled: {exc}")
        return

    created = await scim.create_group("Test-Group", members=["alice@contoso.com"])
    group_id = _extract_id(created)
    display = _extract_display(created)
    print(f"Created group {display} ({group_id})")

    if not group_id:
        print("Group identifier missing; aborting membership updates.")
        return

    update_status = await scim.update_group_members(group_id, add=["bob@contoso.com"])
    print(update_status)

    cleanup_status = await scim.update_group_members(group_id, remove=["alice@contoso.com"])
    print(cleanup_status)


def _extract_id(group: Any) -> str | None:
    if isinstance(group, dict):
        return group.get("id") or group.get("Id")
    return getattr(group, "id", None)


def _extract_display(group: Any) -> str:
    if isinstance(group, dict):
        return group.get("displayName") or group.get("display_name") or "SCIM-Group"
    return getattr(group, "display_name", None) or getattr(group, "displayName", "SCIM-Group")


if __name__ == "__main__":
    asyncio.run(main())
