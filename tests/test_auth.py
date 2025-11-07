import pytest
from fastapi import HTTPException, status

from backend.auth import require_roles, resolve_actor


@pytest.mark.asyncio
async def test_require_roles_accepts_matching_role():
    dependency = require_roles('Admin')
    user = {'roles': ['Admin'], 'preferred_username': 'admin@example.com'}
    assert await dependency(user=user) is user


@pytest.mark.asyncio
async def test_require_roles_rejects_missing_role():
    dependency = require_roles('Operator')
    user = {'roles': ['Viewer']}
    with pytest.raises(HTTPException) as exc_info:
        await dependency(user=user)
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_require_roles_checks_groups():
    dependency = require_roles('viewer')
    user = {'groups': ['Viewer'], 'preferred_username': 'viewer@example.com'}
    assert await dependency(user=user) is user


def test_resolve_actor_falls_back_to_object_id():
    user = {'oid': '1234-5678'}
    assert resolve_actor(user) == '1234-5678'
