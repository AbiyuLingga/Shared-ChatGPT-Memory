# Shared ChatGPT + Mem0 memory

This is a small FastAPI adapter for one Custom GPT and one shared Mem0 vault.
Every Action is protected by Auth0 OAuth. The backend validates the JWT issuer,
audience, signature, time claims, and an allowlist of stable Auth0 `sub` values;
the client cannot select a user or vault.

## Local checks

```text
python -m pip install -r requirements-dev.txt
pytest -q
ruff check app tests
mypy app
```

Run locally with real variables loaded in the shell:

```text
uvicorn app.main:app --factory --reload
```

Never commit `.env` or vendor credentials. Use a non-production Mem0 vault for
smoke testing. Auth0 and GPT editor setup is in `gpt/manual_setup_checklist.md`.

## Deployment

Deploy the Dockerfile to Railway as one Linux replica, set `$PORT`, and provide
all variables from `.env.example` through Railway Variables. Production docs
are disabled; `/health` and `/privacy` remain public. Do not deploy until the
live Google, email/password, allowlist, and later-turn preview/confirm smoke
test passes.
