"""
Authentication system tests.

Tests password hashing, JWT tokens, and integration with the FastAPI app.

Run:  python -m pytest tests/test_auth.py -v
Or:   python tests/test_auth.py
"""
import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api.services.auth import hash_password, verify_password, create_access_token, decode_access_token


def test_password_hashing():
    """Test bcrypt password hashing and verification."""
    pw = hash_password("my_secure_password_123")
    assert pw != "my_secure_password_123"
    assert verify_password("my_secure_password_123", pw)
    assert not verify_password("wrong_password", pw)
    print("[OK] Password hashing and verification")


def test_password_hashing_unique():
    """Test that same password produces different hashes."""
    pw1 = hash_password("test123")
    pw2 = hash_password("test123")
    assert pw1 != pw2
    assert verify_password("test123", pw1)
    assert verify_password("test123", pw2)
    print("[OK] Unique salt per hash")


def test_jwt_create_and_decode():
    """Test JWT creation and decoding."""
    token = create_access_token({"sub": "42", "email": "test@example.com"})
    assert token is not None
    assert len(token) > 20

    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "42"
    assert payload["email"] == "test@example.com"
    assert "exp" in payload
    print("[OK] JWT creation and decoding")


def test_jwt_invalid_token():
    """Test that invalid JWT returns None."""
    result = decode_access_token("this.is.not.a.valid.token")
    assert result is None
    print("[OK] Invalid JWT returns None")


def test_jwt_expiration():
    """Test JWT with custom short expiration."""
    from datetime import timedelta
    token = create_access_token({"sub": "1"}, expires_delta=timedelta(seconds=1))
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "1"
    print("[OK] JWT with custom expiration")


def test_auth_imports():
    """Test that all auth modules import correctly."""
    from api.services.auth import hash_password, verify_password, create_access_token, decode_access_token, JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRY_HOURS
    from api.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, UserResponse
    from api.routes.auth import router
    print("[OK] All auth module imports")


def test_schema_validation():
    """Test Pydantic schema validation."""
    from api.schemas.auth import RegisterRequest, LoginRequest

    # Valid registration
    reg = RegisterRequest(email="user@example.com", password="secure123", full_name="Test User")
    assert reg.email == "user@example.com"
    assert reg.password == "secure123"

    # Valid login
    login = LoginRequest(email="user@example.com", password="secure123")
    assert login.email == "user@example.com"

    print("[OK] Schema validation")


if __name__ == "__main__":
    test_password_hashing()
    test_password_hashing_unique()
    test_jwt_create_and_decode()
    test_jwt_invalid_token()
    test_jwt_expiration()
    test_auth_imports()
    test_schema_validation()
    print("\n" + "=" * 50)
    print("ALL AUTH TESTS PASSED")
    print("=" * 50)