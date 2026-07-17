from src.core.security import create_access_token, decode_access_token, hash_password, verify_password


def test_password_hash_and_jwt_roundtrip():
    encoded = hash_password("secret123")
    assert verify_password("secret123", encoded)
    assert not verify_password("wrong", encoded)
    token = create_access_token("42", "admin")
    assert decode_access_token(token)["sub"] == "42"
