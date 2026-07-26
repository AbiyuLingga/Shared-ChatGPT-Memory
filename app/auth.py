from hmac import compare_digest
from typing import Any

from fastapi import HTTPException

from .config import Settings


class ActionAuthenticator:
    def __init__(
        self, action_api_key: str | None = None, *, settings: Settings | None = None
    ) -> None:
        if settings is not None:
            action_api_key = settings.action_api_key.get_secret_value()
        if not isinstance(action_api_key, str) or not action_api_key:
            raise ValueError("action API key is not configured")
        self._key = action_api_key

    @staticmethod
    def _unauthorized() -> HTTPException:
        return HTTPException(
            status_code=401,
            detail="Invalid or missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    def authenticate(self, authorization: str | None = None) -> dict[str, Any]:
        if not authorization:
            raise self._unauthorized()
        scheme, _, token = authorization.partition(" ")
        if (
            scheme.lower() != "bearer"
            or not token.strip()
            or not compare_digest(token.strip(), self._key)
        ):
            raise self._unauthorized()
        return {"sub": "personal"}


def get_current_user(
    authorization: str | None = None, *, authenticator: ActionAuthenticator | None = None
) -> dict[str, Any]:
    return (authenticator or ActionAuthenticator(settings=Settings())).authenticate(authorization)  # type: ignore[call-arg]
