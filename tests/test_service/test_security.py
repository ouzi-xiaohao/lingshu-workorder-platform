import pytest

from src.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    hash_password_async,
    verify_password,
    verify_password_async,
)


def test_password_hash_and_jwt_roundtrip():
    encoded = hash_password("secret123")
    assert verify_password("secret123", encoded)
    assert not verify_password("wrong", encoded)
    token = create_access_token("42", "admin")
    assert decode_access_token(token)["sub"] == "42"


@pytest.mark.asyncio
async def test_password_helpers_offload_to_thread():
    encoded = await hash_password_async("secret123")
    assert await verify_password_async("secret123", encoded)
    assert not await verify_password_async("wrong", encoded)
