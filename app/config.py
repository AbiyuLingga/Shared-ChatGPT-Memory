from functools import lru_cache
from typing import Any

from pydantic import AliasChoices, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
        hide_input_in_errors=True,
        populate_by_name=True,
    )

    mem0_api_key: SecretStr = Field(validation_alias="MEM0_API_KEY")
    memory_vault_id: str = Field(validation_alias="MEMORY_VAULT_ID", repr=False)
    action_api_key: SecretStr = Field(validation_alias="ACTION_API_KEY", repr=False)
    mem0_base_url: str = Field(default="https://api.mem0.ai", validation_alias="MEM0_BASE_URL")
    contact_email: str = Field(default="", validation_alias="CONTACT_EMAIL")
    change_token_secret: SecretStr = Field(
        validation_alias="CHANGE_TOKEN_SECRET", min_length=32
    )
    environment: str = Field(default="production", validation_alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    request_timeout_seconds: float = Field(
        default=15.0,
        validation_alias=AliasChoices(
            "MEM0_HTTP_TIMEOUT_SECONDS", "REQUEST_TIMEOUT_SECONDS", "MEM0_TIMEOUT_SECONDS"
        ),
        gt=0,
    )
    mem0_add_wait_seconds: float = Field(
        default=5.0, validation_alias="MEM0_ADD_WAIT_SECONDS", ge=0
    )
    mem0_poll_interval_seconds: float = Field(
        default=0.5, validation_alias="MEM0_POLL_INTERVAL_SECONDS", ge=0
    )

    @property
    def mem0_timeout_seconds(self) -> float:
        return self.request_timeout_seconds

    @field_validator("memory_vault_id", "mem0_base_url", mode="before")
    @classmethod
    def reject_blank(cls, value: Any) -> Any:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("value must be non-empty")
        return value.strip()

    @field_validator("action_api_key", mode="before")
    @classmethod
    def reject_blank_action_key(cls, value: Any) -> Any:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("ACTION_API_KEY must be non-empty")
        return value

    @model_validator(mode="after")
    def require_tls_in_production(self) -> "Settings":
        if self.environment.lower() in {"production", "prod"}:
            if not self.mem0_base_url.lower().startswith("https://"):
                raise ValueError("MEM0_BASE_URL must use HTTPS in production")
        return self


AppSettings = Settings


@lru_cache
def get_settings() -> Settings:
    return Settings(_env_file=".env")  # type: ignore[call-arg]
