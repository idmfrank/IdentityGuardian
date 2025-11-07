"""Lightweight SCIM 2.0 data models used for request/response payloads."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class _SCIMBaseModel(BaseModel):
    """Base model with permissive configuration and helper utilities."""

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable representation of the model."""

        return self.model_dump(exclude_none=True)


class User(_SCIMBaseModel):
    schemas: Optional[List[str]] = None
    id: Optional[str] = None
    userName: Optional[str] = None
    name: Optional[Dict[str, Any]] = None
    active: Optional[bool] = None
    emails: Optional[List[Dict[str, Any]]] = None


class Group(_SCIMBaseModel):
    schemas: Optional[List[str]] = None
    id: Optional[str] = None
    displayName: Optional[str] = None
    members: Optional[List[Dict[str, Any]]] = None
