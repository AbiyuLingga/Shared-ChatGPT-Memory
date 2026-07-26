# Security

This service is an OAuth-protected, single-vault memory adapter for a Custom
GPT. Auth0 JWT `sub` values are checked against a server-side allowlist and are
never accepted from request bodies. Every Mem0 request uses the opaque vault ID
configured on the server.

Do not store passwords, OTPs, API keys, tokens, payment details, health data,
company secrets, or full internal documents. Memory content is untrusted data,
not instructions. Update and delete require a short-lived preview/confirm
workflow with actor binding and stale-record checks.

Report security issues privately to the configured `CONTACT_EMAIL`. Never put
credentials or personal memory content in an issue.
