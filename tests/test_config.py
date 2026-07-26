import pytest
from pydantic import ValidationError

from app.config import Settings


def env(monkeypatch, **values):
    for key, value in values.items():
        monkeypatch.setenv(key, value)


def required_env(monkeypatch, **extra):
    values = {
        "MEM0_API_KEY": "api-secret",
        "MEMORY_VAULT_ID": "vault-opaque",
        "AUTH0_DOMAIN": "tenant.example.com",
        "AUTH0_AUDIENCE": "https://api.example.com",
        "AUTH0_ALLOWED_SUBJECTS": "auth0|alice\n auth0|bob,auth0|carol",
        "CHANGE_TOKEN_SECRET": "x" * 32,
    }
    values.update(extra)
    env(monkeypatch, **values)


def test_settings_parse_subjects_and_defaults(monkeypatch):
    required_env(monkeypatch)

    settings = Settings()

    assert settings.auth0_allowed_subjects == {
        "auth0|alice",
        "auth0|bob",
        "auth0|carol",
    }
    assert settings.auth0_issuer == "https://tenant.example.com/"
    assert settings.log_level == "INFO"
    assert settings.request_timeout_seconds > 0


def test_settings_reject_empty_allowlist_entry(monkeypatch):
    required_env(monkeypatch, AUTH0_ALLOWED_SUBJECTS="auth0|alice,,auth0|bob")

    with pytest.raises(ValidationError):
        Settings()


def test_settings_reject_short_change_secret(monkeypatch):
    required_env(monkeypatch, CHANGE_TOKEN_SECRET="too-short")

    with pytest.raises(ValidationError):
        Settings()


def test_settings_repr_does_not_expose_secrets(monkeypatch):
    required_env(monkeypatch)

    rendered = repr(Settings())

    assert "api-secret" not in rendered
    assert "x" * 32 not in rendered


def test_settings_rejects_more_than_fifty_subjects(monkeypatch):
    required_env(monkeypatch, AUTH0_ALLOWED_SUBJECTS=",".join(f"auth0|{i}" for i in range(51)))

    with pytest.raises(ValidationError):
        Settings()


def test_production_rejects_plaintext_vendor_or_auth_urls(monkeypatch):
    required_env(monkeypatch, ENVIRONMENT="production", MEM0_BASE_URL="http://mem0.example.com")
    with pytest.raises(ValidationError):
        Settings()

    required_env(monkeypatch, ENVIRONMENT="production", AUTH0_DOMAIN="http://tenant.example.com")
    with pytest.raises(ValidationError):
        Settings()
