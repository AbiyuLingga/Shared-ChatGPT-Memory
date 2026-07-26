# Personal static API key implementation plan

## Goal

Replace Auth0/OIDC with one server-side `ACTION_API_KEY` for this personal,
single-vault deployment. Keep every memory route protected and keep the vault
selector server-side.

## Tasks

1. Replace Auth0 settings and JWT/JWKS validation with `SecretStr` API-key
   configuration and constant-time bearer comparison. Return `401` with a
   Bearer challenge for missing or invalid credentials.
2. Wire the authenticator into the app factory and preserve the fixed
   `personal` subject marker used for rate limiting and audit fields.
3. Remove Auth0-only dependency, environment variables, smoke-test wording,
   and documentation. Describe the key limitation and rotation procedure.
4. Update GPT OpenAPI/setup instructions to configure the bearer key, then run
   pytest, Ruff, mypy, and a repository-wide Auth0 reference search.

## Verification

- Missing, malformed, and wrong keys return `401`.
- Correct key authenticates as the fixed personal marker.
- All existing memory/change/security tests pass.
- No Auth0/JWT dependency or runtime configuration remains.
