from datetime import datetime, timedelta, timezone

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException

from app.auth import Authenticator


class FakeJWKS:
    def __init__(self, key):
        self.key = key

    def get_signing_key_from_jwt(self, token):
        return type("SigningKey", (), {"key": self.key})()


@pytest.fixture
def keys():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def make_token(private_key, subject="auth0|alice", **claims):
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iss": "https://tenant.example.com/",
        "aud": "https://api.example.com",
        "iat": now,
        "exp": now + timedelta(minutes=5),
    }
    payload.update(claims)
    return jwt.encode(payload, private_key, algorithm="RS256", headers={"kid": "test"})


def authenticator(private_key, subjects=("auth0|alice",)):
    signing_key = private_key.public_key() if private_key is not None else None
    return Authenticator(
        domain="tenant.example.com",
        audience="https://api.example.com",
        allowed_subjects=set(subjects),
        jwks_client=FakeJWKS(signing_key),
    )


def test_missing_token_is_401_with_bearer_challenge():
    with pytest.raises(HTTPException) as caught:
        authenticator(None).authenticate(None)

    assert caught.value.status_code == 401
    assert caught.value.headers["WWW-Authenticate"] == "Bearer"


def test_invalid_token_is_401():
    with pytest.raises(HTTPException) as caught:
        authenticator(None).authenticate("Bearer not-a-jwt")

    assert caught.value.status_code == 401


def test_valid_token_for_allowlisted_subject_returns_claims(keys):
    token = make_token(keys)

    claims = authenticator(keys).authenticate(f"Bearer {token}")

    assert claims["sub"] == "auth0|alice"


def test_valid_token_for_non_allowlisted_subject_is_403(keys):
    token = make_token(keys, subject="auth0|mallory")

    with pytest.raises(HTTPException) as caught:
        authenticator(keys).authenticate(f"Bearer {token}")

    assert caught.value.status_code == 403


def test_required_subject_and_exact_issuer_are_enforced(keys):
    for claims in (
        {"sub": None},
        {"iss": "https://other.example.com/"},
        {"iat": None},
    ):
        token = make_token(keys, **claims)
        with pytest.raises(HTTPException) as caught:
            authenticator(keys).authenticate(f"Bearer {token}")
        assert caught.value.status_code == 401
