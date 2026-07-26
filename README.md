# Shared ChatGPT Memory

A small FastAPI service that connects a Custom GPT to one shared Mem0 memory
vault.

Use it for preferences, decisions, workflows, and light project context. For
example:

> "Remember that I prefer short and direct answers."

## How it works

```text
ChatGPT Custom GPT -> FastAPI backend -> Mem0
```

The Custom GPT searches relevant memories and saves new memories when needed.
Changes and deletions use a preview/confirm workflow.

## Quick setup

1. Deploy the repository to a public HTTPS host such as Railway.
2. Add the variables from [.env.example](.env.example).
3. Check the deployment:

   ```text
   https://your-domain/health
   https://your-domain/privacy
   ```

4. In the Custom GPT editor, open **Configure -> Actions -> Create new action**.
5. Import [gpt/action.openapi.yaml](gpt/action.openapi.yaml).
6. Replace the `servers` URL with your public backend URL.
7. Configure authentication as **API Key -> Bearer** using your server's
   `ACTION_API_KEY`.
8. Copy [gpt/instructions.md](gpt/instructions.md) into the GPT's
   **Instructions** field.
9. Set the Privacy Policy URL to `https://your-domain/privacy`.

The complete checklist is in [gpt/manual_setup_checklist.md](gpt/manual_setup_checklist.md).

## Example prompts

- "Remember that I prefer short and direct answers."
- "What do you remember about my answer style?"
- "Change my answer preference to short, critical, and direct."
- "Forget my answer preference."

GPT Actions may not run on every message. When an Action is unavailable, the GPT
continues using the current conversation context.

## Local development

```text
python -m pip install -r requirements-dev.txt
uvicorn app.main:app --factory --reload
```

Run the checks:

```text
pytest -q
ruff check app tests
mypy app
```

Never commit `.env` or real vendor credentials.

## Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /health` | Health check |
| `GET /privacy` | Privacy notice |
| `POST /v1/memories/search` | Search memories |
| `POST /v1/memories` | Add a memory |
| `POST /v1/memory-changes/preview` | Preview an update or deletion |
| `POST /v1/memory-changes/confirm` | Confirm an update or deletion |

See [SECURITY.md](SECURITY.md), [PRIVACY.md](PRIVACY.md), and
[IMPLEMENTATION_REPORT.md](IMPLEMENTATION_REPORT.md) for additional project
documentation.
