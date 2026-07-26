from collections.abc import Callable
from typing import Any

import jwt
from fastapi import HTTPException

from .config import Settings


class Authenticator:
    def __init__(
        self,
        settings: Settings | None = None,
        *,
        domain: str | None = None,
        audience: str | None = None,
        allowed_subjects: set[str] | frozenset[str] | None = None,
        jwks_client: Any | None = None,
        token_source: Callable[[], str | None] | None = None,
    ) -> None:
        if settings is not None:
            domain = settings.auth0_domain
            audience = settings.auth0_audience
            allowed_subjects = settings.auth0_allowed_subjects
            ttl = settings.jwks_cache_ttl_seconds
        else:
            ttl = 300
        if not domain or not audience or allowed_subjects is None:
            raise ValueError("auth configuration is incomplete")
        authority = domain.rstrip("/")
        self.issuer = f"{authority if authority.startswith(('http://', 'https://')) else f'https://{authority}'}/"
        self.audience = audience
        self.allowed_subjects = frozenset(allowed_subjects)
        self.token_source = token_source
        self.jwks_client = jwks_client or jwt.PyJWKClient(
            f"{self.issuer}.well-known/jwks.json", cache_jwk_set=True, lifespan=ttl
        )

    @staticmethod
    def _unauthorized() -> HTTPException:
        return HTTPException(
            status_code=401,
            detail="Invalid or missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    def _get_token(self, authorization: str | None) -> str:
        if self.token_source is not None:
            authorization = self.token_source()
        if not authorization:
            raise self._unauthorized()
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token.strip():
            raise self._unauthorized()
        return token.strip()

    def authenticate(self, authorization: str | None = None) -> dict[str, Any]:
        token = self._get_token(authorization)
        try:
            signing_key = self.jwks_client.get_signing_key_from_jwt(token).key
            claims = jwt.decode(
                token,
                signing_key,
                algorithms=["RS256"],
                audience=self.audience,
                issuer=self.issuer,
                options={"require": ["sub", "exp", "iat"], "verify_iat": True},
            )
        except Exception:
            raise self._unauthorized() from None
        subject = claims.get("sub")
        if not isinstance(subject, str) or not subject:
            raise self._unauthorized()
        if subject not in self.allowed_subjects:
            raise HTTPException(status_code=403, detail="Forbidden")
        return dict(claims)


def get_current_user(
    authorization: str | None = None, *, authenticator: Authenticator | None = None
) -> dict[str, Any]:
    """Small dependency-friendly wrapper; applications can inject an Authenticator."""
    return (authenticator or Authenticator(settings=Settings())).authenticate(authorization)  # type: ignore[call-arg]
