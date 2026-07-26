import pytest
from fastapi import HTTPException

from app.auth import ActionAuthenticator


def test_missing_token_is_401_with_bearer_challenge():
    with pytest.raises(HTTPException) as caught:
        ActionAuthenticator("secret-key").authenticate(None)

    assert caught.value.status_code == 401
    assert caught.value.headers["WWW-Authenticate"] == "Bearer"


def test_invalid_token_is_401():
    with pytest.raises(HTTPException) as caught:
        ActionAuthenticator("secret-key").authenticate("Bearer wrong-key")

    assert caught.value.status_code == 401


def test_valid_token_returns_fixed_personal_marker():
    claims = ActionAuthenticator("secret-key").authenticate("Bearer secret-key")

    assert claims == {"sub": "personal"}


def test_wrong_scheme_is_401():
    with pytest.raises(HTTPException) as caught:
        ActionAuthenticator("secret-key").authenticate("Basic secret-key")

    assert caught.value.status_code == 401
