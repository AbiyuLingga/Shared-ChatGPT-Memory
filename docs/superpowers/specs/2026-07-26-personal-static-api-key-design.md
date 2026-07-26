# Personal Shared Memory Authentication Design

## Decision

Replace Auth0/OIDC with one static `ACTION_API_KEY` because this deployment is
for one private owner. Keep authentication enabled; do not expose the memory
API anonymously.

## Runtime flow

Custom GPT sends:

```text
Authorization: Bearer <ACTION_API_KEY>
```

FastAPI compares the supplied value with the server-side `ACTION_API_KEY` using
constant-time comparison. Missing or invalid keys return `401` with a Bearer
challenge. A valid key can access the one fixed Mem0 vault configured by
`MEMORY_VAULT_ID`; request bodies cannot select a user or vault.

## Scope changes

- Remove Auth0 settings, JWKS validation, subject allowlisting, and Auth0 setup
  instructions from the application.
- Remove Auth0-specific dependencies and tests where no longer applicable.
- Add `ACTION_API_KEY` as a required secret setting and update local/Railway
  environment documentation.
- Keep Mem0 fixed-vault filtering, explicit `infer=false`, deduplication,
  bounded change preview/confirm, rate limiting, security headers, and disabled
  production documentation.
- Keep the four GPT Actions: search, add, preview, and confirm.
- Change GPT setup instructions to API-key authentication.

## Security boundary

The static key authenticates the GPT integration, not an individual person.
Anyone who obtains the key can read and mutate the shared vault. The key must
never be committed, logged, or placed in the OpenAPI document. Rotate it before
production if it has been exposed. This design has no per-user identity,
per-user privacy, or actor-level audit trail.

## Configuration

Required authentication setting:

```env
ACTION_API_KEY=<random-secret>
```

Retained settings include `MEM0_API_KEY`, `MEMORY_VAULT_ID`,
`CHANGE_TOKEN_SECRET`, Mem0 timeout/poll settings, environment, logging level,
and privacy contact. Auth0 variables are removed from the runtime baseline.

## Verification

Tests must cover missing, invalid, and valid API keys, fixed vault behavior,
request attempts to supply `user_id`, and unchanged memory safety/reliability
guarantees. Run the full pytest, Ruff, and mypy checks after implementation.
