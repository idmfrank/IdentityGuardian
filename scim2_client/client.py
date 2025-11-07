"""HTTP-based SCIM 2.0 client compatible with the expectations of IdentityGuardian."""
from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping, MutableMapping, Optional

import httpx

PATCH_SCHEMA = "urn:ietf:params:scim:api:messages:2.0:PatchOp"


def _model_dump(model: Any) -> MutableMapping[str, Any]:
    """Return a JSON-serialisable dictionary for supported model types."""

    if model is None:
        return {}
    if hasattr(model, "to_dict"):
        return model.to_dict()  # type: ignore[return-value]
    if hasattr(model, "model_dump"):
        return model.model_dump(exclude_none=True)  # type: ignore[return-value]
    if isinstance(model, Mapping):
        return dict(model)
    raise TypeError(f"Unsupported SCIM model type: {type(model)!r}")


class Client:
    """Simple synchronous SCIM client built on top of httpx."""

    def __init__(
        self,
        base_url: str,
        *,
        bearer_token: Optional[str] = None,
        timeout: Optional[float] = 10.0,
    ) -> None:
        if not base_url:
            raise ValueError("base_url is required")

        self.base_url = base_url.rstrip("/")
        self.bearer_token = bearer_token
        self.timeout = timeout

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/scim+json, application/json",
            "Content-Type": "application/scim+json",
        }
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        return headers

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        json: Any = None,
    ) -> Any:
        if not path.startswith("/"):
            path = "/" + path
        url = f"{self.base_url}{path}"

        response = httpx.request(
            method,
            url,
            headers=self._headers(),
            params=params,
            json=json,
            timeout=self.timeout,
        )
        response.raise_for_status()

        if response.content:
            content_type = response.headers.get("Content-Type", "")
            if "json" in content_type:
                try:
                    return response.json()
                except ValueError:
                    return response.text
            return response.text
        return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def create_user(self, user: Any) -> Any:
        payload = _model_dump(user)
        return self._request("POST", "/Users", json=payload)

    def update_user(self, user_id: str, user: Any) -> Any:
        payload = _model_dump(user)
        return self._request("PUT", f"/Users/{user_id}", json=payload)

    def patch_user(self, user_id: str, operations: Iterable[Mapping[str, Any]]) -> Any:
        patch_body = {
            "schemas": [PATCH_SCHEMA],
            "Operations": list(operations),
        }
        return self._request("PATCH", f"/Users/{user_id}", json=patch_body)

    def list_groups(self, *, filter: Optional[str] = None) -> Any:
        params = {"filter": filter} if filter else None
        return self._request("GET", "/Groups", params=params) or {}

    def create_group(self, group: Any) -> Any:
        payload = _model_dump(group)
        return self._request("POST", "/Groups", json=payload)

    def patch_group(self, group_id: str, operations: Iterable[Mapping[str, Any]]) -> Any:
        patch_body = {
            "schemas": [PATCH_SCHEMA],
            "Operations": list(operations),
        }
        return self._request("PATCH", f"/Groups/{group_id}", json=patch_body)

    def delete_group(self, group_id: str) -> Any:
        return self._request("DELETE", f"/Groups/{group_id}")
