# Manual setup checklist

1. Create a dedicated Auth0 tenant, custom API (stable identifier), Regular Web
   Application, database connection, and Google connection. Disable database
   self-signup and enable MFA for allowed accounts.
2. Set the Auth0 API audience as the application's default audience. Verify a
   real Universal Login token has the exact issuer and audience configured in
   Railway.
3. Generate an opaque 128-bit `MEMORY_VAULT_ID` and a random
   `CHANGE_TOKEN_SECRET` (at least 32 characters). Add only approved `sub`
   values to `AUTH0_ALLOWED_SUBJECTS`, one per line.
4. Create a non-production Mem0 test vault and put its API key in Railway
   Variables. Keep all secrets out of Git, Docker build args, and logs.
5. Deploy one Linux replica to Railway with HTTPS and a `$PORT` health check.
   Confirm `/health` is public and `/privacy` is public; `/docs`, `/redoc`, and
   `/openapi.json` must be unavailable in production.
6. Import `action.openapi.yaml` into the Custom GPT. Configure OAuth with:
   - Authorization URL `https://<tenant>.auth0.com/authorize`
   - Token URL `https://<tenant>.auth0.com/oauth/token`
   - Scope `openid`
   - The callback URL shown by the GPT editor
7. Run the non-production live smoke test with both Google and email/password,
   including a disallowed subject, shared search, preview, later-turn confirm,
   and delete. Do not deploy production data until all checks pass.
