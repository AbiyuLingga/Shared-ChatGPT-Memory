# Manual setup checklist

1. Generate a long random `ACTION_API_KEY`, an opaque 128-bit
   `MEMORY_VAULT_ID`, and a random `CHANGE_TOKEN_SECRET` (at least 32
   characters). Put them in Railway Variables and never in Git.
2. Create a non-production Mem0 test vault and put its API key in Railway
   Variables. Keep all secrets out of Git, Docker build args, and logs.
3. Deploy one Linux replica to Railway with HTTPS and a `$PORT` health check.
   Confirm `/health` is public and `/privacy` is public; `/docs`, `/redoc`, and
   `/openapi.json` must be unavailable in production.
4. Import `action.openapi.yaml` into the Custom GPT. Configure API-key
   authentication using the `Authorization` header with value
   `Bearer <ACTION_API_KEY>`.
5. Run the non-production live smoke test with the configured key, shared
   search, preview, later-turn confirm, and delete. Do not deploy production
   data until all checks pass.
