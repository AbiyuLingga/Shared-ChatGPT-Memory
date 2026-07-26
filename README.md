# Shared ChatGPT + Mem0 memory

This is a small FastAPI adapter for one Custom GPT and one shared Mem0 vault.
Every Action is protected by one server-side bearer API key; the client cannot
select a user or vault.

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
smoke testing. GPT editor setup is in `gpt/manual_setup_checklist.md`.

## Deployment

Deploy the Dockerfile to Railway as one Linux replica, set `$PORT`, and provide
all variables from `.env.example` through Railway Variables. Production docs
are disabled; `/health` and `/privacy` remain public. Do not deploy until the
live bearer-key and later-turn preview/confirm smoke test passes. Anyone who
obtains the key can access the shared vault, so rotate
it immediately if exposed.
