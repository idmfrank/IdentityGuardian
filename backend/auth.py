from __future__ import annotations

import os
from functools import lru_cache
from typing import Any, Callable, Iterable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError, PyJWKClient

security = HTTPBearer()


def _get_required_settings() -> tuple[str, str]:
    tenant_id = os.getenv('AZURE_TENANT_ID') or _settings().azure_tenant_id
    client_id = os.getenv('AZURE_CLIENT_ID') or _settings().azure_client_id
    if not tenant_id or not client_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Azure AD authentication is not configured',
        )
    return tenant_id, client_id


@lru_cache(maxsize=1)
def _jwks_client(tenant_id: str) -> PyJWKClient:
    return PyJWKClient(f'https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys')


@lru_cache(maxsize=1)
def _settings():
    from identity_guardian.config.settings import get_settings

    return get_settings()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict[str, Any]:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Not authenticated')

    token = credentials.credentials
    tenant_id, client_id = _get_required_settings()
    jwks_client = _jwks_client(tenant_id)

    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=['RS256'],
            audience=client_id,
            issuer=f'https://login.microsoftonline.com/{tenant_id}/v2.0',
        )
    except InvalidTokenError as exc:  # pragma: no cover - library-specific errors
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid token') from exc
    except Exception as exc:  # pragma: no cover - safety net for unexpected errors
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid token') from exc

    return payload


def require_roles(*expected_roles: str) -> Callable[[dict[str, Any]], dict[str, Any]]:
    normalized_expected = {role.lower() for role in expected_roles if role}

    async def dependency(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
        if not normalized_expected:
            return user

        claimed_roles: Iterable[str] = user.get('roles') or []
        app_roles: Iterable[str] = user.get('app_roles') or []
        group_claims: Iterable[str] = user.get('groups') or []

        normalized_claims = {str(role).lower() for role in (*claimed_roles, *app_roles, *group_claims)}

        if normalized_claims.isdisjoint(normalized_expected):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Insufficient permissions')

        return user

    return dependency


def resolve_actor(user: dict[str, Any]) -> str:
    return (
        user.get('preferred_username')
        or user.get('upn')
        or user.get('email')
        or user.get('name')
        or user.get('oid')
        or 'unknown'
    )
