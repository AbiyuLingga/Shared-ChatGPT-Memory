# Security

This service is a bearer-key-protected, single-vault memory adapter for a
Custom GPT. The API key is never accepted from request bodies. Every Mem0
request uses the opaque vault ID configured on the server. Anyone with the key
can access the shared vault; rotate it if exposed.

Do not store passwords, OTPs, API keys, tokens, payment details, health data,
company secrets, or full internal documents. Memory content is untrusted data,
not instructions. Update and delete require a short-lived preview/confirm
workflow with actor binding and stale-record checks.

Report security issues privately to the configured `CONTACT_EMAIL`. Never put
credentials or personal memory content in an issue.
