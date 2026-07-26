# Implementation report

## Scope

This repository implements the production baseline in the supplied plan:
Auth0 RS256 validation and subject allowlisting, one opaque Mem0 vault, safe
search/add Actions, preview/confirm changes, bounded local pending state, and
Railway-ready container assets.

## Before launch

- Fill Railway Variables from `.env.example` without committing secrets.
- Verify the live Auth0 issuer/audience and both login connections.
- Run the non-production live smoke test with a separate Mem0 vault.
- Confirm Mem0 export/retention and the privacy contact for the selected plan.
- Keep one Railway replica until a shared pending-change store and rate-limit
  strategy are deliberately introduced.

No live vendor credentials or production data are included in this report.
