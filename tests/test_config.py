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
        "ACTION_API_KEY": "action-secret",
        "CHANGE_TOKEN_SECRET": "x" * 32,
        **extra,
    }
    env(monkeypatch, **values)


def test_settings_parse_static_key_and_defaults(monkeypatch):
    required_env(monkeypatch)

    settings = Settings()

    assert settings.action_api_key.get_secret_value() == "action-secret"
    assert settings.log_level == "INFO"
    assert settings.request_timeout_seconds > 0


def test_settings_reject_empty_action_key(monkeypatch):
    required_env(monkeypatch, ACTION_API_KEY=" ")

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
    assert "action-secret" not in rendered
    assert "x" * 32 not in rendered
