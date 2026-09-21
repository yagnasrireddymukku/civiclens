# ADR-009: Authentication Strategy

## Status
Accepted

## Context
CivicLens needs authenticated features (tracking, saved items, personal
dashboard, admin/editor review tooling) while keeping most content
publicly accessible and indexable for SEO without login.

## Decision
Use **JWT-based authentication** (short-lived access token + longer-lived
refresh token, stored per [SECURITY.md](../SECURITY.md) cookie/storage
guidance), issued by the FastAPI backend. Roles: `user` (default),
`editor` (can review/approve ingestion changes), `admin` (full access) —
a minimal RBAC model, extended only when a real permission boundary is
needed. Email/password as the baseline login method; OAuth (starting with
Google) as an additive, secondary option, not a replacement.

## Alternatives Considered
- **Session-based auth with server-side session store**: viable
  alternative; JWT chosen for statelessness that suits a decoupled
  Next.js/FastAPI deployment without adding a session store (e.g., Redis)
  as a new dependency at MVP.
- **Third-party auth-as-a-service (e.g., Auth0, Clerk)**: reasonable
  option, deferred — introduces a paid external dependency and data-
  residency questions for a product handling Indian citizens' profile data;
  revisit if in-house auth maintenance becomes a real burden.
- **Fine-grained permissions system (per-resource ACLs) at launch**:
  rejected — three roles cover all currently specified needs
  ([PRODUCT_REQUIREMENTS.md](../PRODUCT_REQUIREMENTS.md)); avoid
  overengineering ([CLAUDE.md](../../CLAUDE.md)).

## Consequences
- Public content requires no authentication and remains fully
  crawlable/SEO-friendly.
- Refresh-token handling, secure cookie flags, and token revocation must be
  implemented per [SECURITY.md](../SECURITY.md) — JWT statelessness makes
  revocation (e.g., on password change) a deliberate design point (short
  access-token TTL + refresh-token allowlist/denylist).
- RBAC roles map directly onto the ingestion review workflow
  ([DATA_SOURCES.md](../DATA_SOURCES.md) §4): only `editor`/`admin` can
  approve publishes.
