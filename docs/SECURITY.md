# CivicLens — Security Architecture

Companion to [PRIVACY.md](PRIVACY.md). Defines the target security
architecture for CivicLens — authentication, authorization, input
handling, abuse prevention, and operational hygiene. Implements
[PRODUCT_REQUIREMENTS.md](PRODUCT_REQUIREMENTS.md) §2.4 (NFR-SEC1–SEC-n)
and is the authoritative source for the cookie/storage guidance referenced
by [ADR-009](ADR/ADR-009-authentication-strategy.md).

**No application code exists yet.** This is target design for every phase
from Phase 2 onward, formally reviewed and hardened in Phase 15 (§13,
[ROADMAP.md](ROADMAP.md) Phase 15) — security is a running concern
throughout, not a bolt-on at the end.

## 1. Principles

1. **Never trust client input** — every boundary is validated server-side
   regardless of frontend validation.
2. **Least privilege by default** — new endpoints require auth and the
   narrowest role that satisfies the need.
3. **Defense in depth** — input validation, authz, and rate limiting are
   independent layers, not substitutes for each other.
4. **Secrets never enter source control** (§7; [CLAUDE.md](../CLAUDE.md)
   rules 14–15).
5. **Fail closed** — an ambiguous authz/validation outcome denies.
6. **Data minimization is a security control** — data never collected
   ([PRIVACY.md](PRIVACY.md) §1) cannot leak.

## 2. Authentication

Per [ADR-009](ADR/ADR-009-authentication-strategy.md): JWT access +
refresh tokens, email/password baseline, OAuth (Google) as a secondary,
additive login method.

- **Access token**: TTL **~15 minutes**. Carries `sub`, `role`, `iat`,
  `exp`, a token-family id — never profile attributes
  ([DATABASE.md](DATABASE.md) §2.8).
- **Refresh token**: TTL **~30 days**, **rotated on every use** (old token
  invalidated, new one issued); a replayed already-rotated token signals
  compromise and revokes its whole token family. Stored **hashed**
  server-side, never plaintext.
- **Passwords**: adaptive salted hash (bcrypt/argon2), never reversible
  encryption or a fast general-purpose hash.
- **OAuth**: additive only — always results in a CivicLens-issued JWT
  pair; a third-party token is never accepted directly for authorization.

## 3. Token Storage & CSRF

- Access and refresh tokens are set as **httpOnly, Secure,
  SameSite=Lax cookies**, never `localStorage`/`sessionStorage` — removes
  the common XSS-reads-token-from-storage vector.
- Because cookies attach automatically, state-changing requests
  (`POST`/`PUT`/`PATCH`/`DELETE`) require a **CSRF token** (double-submit/
  synchronizer pattern, sent as an `X-CSRF-Token` header) in addition to
  `SameSite=Lax`. Public `GET` endpoints are unaffected — auth is additive
  ([ARCHITECTURE.md](ARCHITECTURE.md) §2).

## 4. Authorization (RBAC)

Roles: `user` (default), `editor` (change-record review, entity
verification — [DATA_SOURCES.md](DATA_SOURCES.md) §4), `admin` (full
access — no capability exists yet that `editor` cannot also do; the two
are already distinct roles so a future admin-only action has somewhere
to attach without a schema change).

- **Realized (Phase 13, review/approval half):**
  `app.auth.dependencies.require_role(*allowed_roles)` is the RBAC
  dependency every privileged route declares — no implicit
  "authenticated ⇒ authorized." It composes with `get_current_user`
  (never duplicates its cookie/token logic) and always reads
  `current_user.role` fresh from the database, never from the JWT's
  own claims — a revoked/changed role takes effect on the very next
  request rather than waiting out the access token's TTL. Every
  `/api/v1/admin/*` route (`app.api.v1.admin`,
  [API.md](API.md) §21) uses it; a `user` gets `403`, verified by a
  dedicated test that also confirms two independent sessions never
  cross-contaminate roles.
- Every authenticated route declares its minimum required role explicitly
  (e.g., a `require_role(...)` dependency) — no implicit "authenticated ⇒
  authorized."
- **Resource ownership** is enforced alongside role: a `user` may only
  read/modify their own `profiles`, `saved_items`, `tracking_items`,
  `notifications` ([DATABASE.md](DATABASE.md) §2.8). `/admin/*` routes
  are a role check, not an ownership check — `editor`/`admin` can see
  every entity/record, so there is no per-object ownership to hide (no
  404-for-both-cases IDOR pattern applies there; a role failure is a
  plain `403`).
- `editor`/`admin` actions are enforced at the API layer, not only hidden
  in the UI. No per-resource ACL system exists or is planned at this
  scale ([ADR-009](ADR/ADR-009-authentication-strategy.md)).
- **No approval without evidence**: `app.admin.service.submit_verification`
  requires a real `source_id` (`VerificationRecord.source_id` is
  `nullable=False` at the column level, and the function additionally
  checks it resolves to a real `Source` row) before recording any
  verification decision — a fabricated or missing evidence reference is
  rejected (`422`), never silently accepted.

## 5. Input Validation & Injection Prevention

- Every API boundary (body, query, path params) is a **Pydantic schema**
  — no handler reads raw/untyped request data. Client-side validation is
  UX convenience only.
- **SQL injection**: all DB access goes through SQLAlchemy parameterized
  queries/ORM constructs; raw string-interpolated SQL is prohibited.
- **XSS**: Next.js's default JSX escaping handles output encoding;
  `dangerouslySetInnerHTML` requires an explicit sanitizer and
  justification. A **Content-Security-Policy** header restricts script
  sources and disallows inline scripts as a second layer.
- **CSRF**: see §3.
- Command/path injection is not currently applicable (no shell-out or
  user-controlled file paths); revisited if uploads are introduced (§10).

## 6. Rate Limiting & API Abuse Prevention

Per endpoint class and identity (user id when authenticated, else IP):

- **Auth endpoints** (login/refresh/reset/signup): tight per-IP and
  per-account limits against credential stuffing/brute force.
- **Public reads** (search, listings): generous but capped, to allow
  normal browsing while bounding scraping/load abuse.
- **AI endpoints** ([AI_ARCHITECTURE.md](AI_ARCHITECTURE.md)): the
  strictest per-user limits, since every request has real inference cost;
  enforced independently of general limits and monitored for cost
  anomalies (see [OBSERVABILITY.md](OBSERVABILITY.md) §AI usage
  monitoring, referenced from
  [AI_ARCHITECTURE.md](AI_ARCHITECTURE.md) §7).
- **Writes** (tracking, saved items, profile updates): moderate per-user
  limits.

Enforced at the application layer at minimum (FastAPI middleware/
dependency); an edge/proxy layer is an operational addition belonging to
[DEPLOYMENT.md](DEPLOYMENT.md). Limit breaches return `429` with
`Retry-After`, never a silent drop.

## 7. Secrets Management

- Secrets (DB credentials, JWT signing keys, OAuth secret, LLM provider
  keys) are supplied via environment variables, never hardcoded/committed.
  `.env.example` holds placeholders only ([CLAUDE.md](../CLAUDE.md) rules
  14–15).
- Production secrets are expected to live in a managed secrets store;
  exact provider/mechanism is a [DEPLOYMENT.md](DEPLOYMENT.md) /
  [ADR-010](ADR/ADR-010-deployment-architecture.md) decision, not defined
  here.
- JWT signing keys are rotatable: verification accepts a current and
  previous key during a rotation window.
- No secret is ever written to logs, error reports, or traces — reviewed
  specifically at Phase 15 (§13).

## 8. Encryption

- **In transit**: TLS everywhere — browser↔frontend, frontend↔API,
  API↔database. No plaintext HTTP outside local dev.
- **At rest**: relies on the managed PostgreSQL provider's at-rest
  encryption ([ADR-004](ADR/ADR-004-postgresql.md)); no application-level
  column encryption today, since no currently-collected field
  ([PRIVACY.md](PRIVACY.md) §2) has a named requirement justifying it.
  Revisit if a future field needs it.
- Password hashes and hashed refresh tokens are non-recoverable by
  construction regardless of DB-level encryption.

## 9. Audit Logging

Two distinct trails:

1. **Data-change audit** — `change_records` ([DATABASE.md](DATABASE.md)
   §2.7, §5) captures every material change to a published fact:
   who/what reviewed it, when applied. A governance requirement
   ([DATA_GOVERNANCE.md](DATA_GOVERNANCE.md) §8) as much as a security one.
2. **Auth/access audit** — login success/failure, token refresh/
   revocation, password change, role change, and privileged
   `editor`/`admin` actions are logged with actor, timestamp, outcome —
   never full credentials, raw tokens, or full sensitive request bodies.

Retention/rotation mechanics are an [OBSERVABILITY.md](OBSERVABILITY.md)
operational detail, not defined here.

## 10. Secure File Handling

**Out of scope today.** No upload feature exists in
[PRODUCT_REQUIREMENTS.md](PRODUCT_REQUIREMENTS.md) or
[DATABASE.md](DATABASE.md) §6 (Document Intelligence is checklists, not
file storage/OCR). If a future phase introduces uploads, this section must
be filled in first, covering: file-type allowlisting, size limits,
malware scanning, storage outside the web root or via signed URLs, and
validating actual content type rather than trusting extension/declared
MIME type.

## 11. AI-Specific Security

Detail lives in [AI_ARCHITECTURE.md](AI_ARCHITECTURE.md) §7; referenced,
not duplicated:

- **Prompt injection**: retrieved content is treated as data, never
  instructions; the system prompt is structurally separated from
  retrieved/user content.
- **Data isolation**: a user's `profiles` data is used only in their own
  request, never to answer another user's query or to train/fine-tune a
  model ([PRIVACY.md](PRIVACY.md) §7).
- **Rate limiting/cost control**: see §6.
- **Provider abstraction as a security boundary**: the LLM provider API
  key is confined to the single `LLMProvider` interface
  ([AI_ARCHITECTURE.md](AI_ARCHITECTURE.md) §5), not scattered across the
  codebase.

## 12. Dependency & Supply-Chain Hygiene

- New dependencies must be justified against the existing stack
  ([CLAUDE.md](../CLAUDE.md) rule 13) — each is additional attack surface.
- CI runs dependency vulnerability scanning (e.g., `pip-audit`/`safety`,
  `npm audit`) once CI exists (Phase 1), gating merges on critical
  findings.
- Lockfiles are committed so dependency changes are visible in diffs.
- Third-party SDKs (auth-as-a-service, analytics) are evaluated for what
  data they'd receive ([PRIVACY.md](PRIVACY.md) §1) before adoption.

## 13. Security Review Checklist (Phase 15)

[ROADMAP.md](ROADMAP.md) Phase 15 is a formal review pass, not the first
application of these controls. Minimum verification set:

- [ ] Every non-public endpoint enforces authn + correct RBAC role and
      resource ownership (§4).
- [ ] Token TTLs, rotation, and revocation-on-password-change/
      logout-everywhere behave as specified (§2).
- [ ] Cookie flags and CSRF protection are present on all state-changing
      routes (§3).
- [ ] All inputs are Pydantic-validated; no raw-payload handlers (§5).
- [ ] No raw SQL string interpolation exists anywhere (§5).
- [ ] CSP/output-encoding verified in the deployed frontend, not just dev.
- [ ] Rate limits tested for auth, public, write, and AI classes (§6).
- [ ] No secret in source history, CI logs, or app logs (§7).
- [ ] TLS enforced end-to-end in every non-local environment (§8).
- [ ] `change_records` and auth/access audit logs populate correctly (§9).
- [ ] Dependency scan has no open critical/high findings (§12).
- [ ] Account deletion/export flows verified end-to-end
      ([PRIVACY.md](PRIVACY.md) §4–§5).
- [ ] Penetration-test-style pass covering injection and auth/authz bypass
      across every module.

Acceptance is "no critical/high findings open" ([ROADMAP.md](ROADMAP.md));
findings are fixed forward, not rolled back.

## 14. Explicitly Not Built Yet

- **Realized (Tracking + Notifications, rescheduled from Phase 12):**
  §2-4's JWT/cookie/CSRF design is now implemented
  (`app.auth`) exactly as specified above, verified by a real replay-
  attack test (§2's "replayed already-rotated token revokes its whole
  token family") and a live smoke test exercising the full cookie/CSRF
  flow end to end. Not yet real: OAuth login (still deferred, per
  ADR-009's own "secondary, additive" framing — email/password is the
  only login method); argon2 as a password-hash alternative (bcrypt
  only, currently).
- **Realized (Phase 13, review/approval half):** the RBAC piece §4
  above describes — `require_role`, gating every `/api/v1/admin/*`
  route. Still not real: any `editor`/`admin`-gated route outside
  `/admin/*` (e.g. a re-indexing route for `/ai` — the dependency
  exists and could gate one, but no route calls it there yet); the
  ingestion-pipeline-specific privileged actions
  [DATA_SOURCES.md](DATA_SOURCES.md) §4 describes (source onboarding,
  fetch approval) — no ingestion pipeline exists for them to gate.
- No secrets manager, WAF, or general rate-limiting infrastructure is
  provisioned. Phase 12 added one deliberately minimal exception: an
  in-process, single-instance, per-IP sliding-window limiter scoped only
  to `/api/v1/ai/*` (`app.ai.rate_limit`) — disclosed as an MVP, not a
  claim that rate-limiting infrastructure now exists generally (it does
  not coordinate across processes/instances and covers no other route).
  Phase 13 added a second, deliberately separate instance of the same
  pattern for mutating `/api/v1/admin/*` routes
  (`app.admin.rate_limit.enforce_admin_rate_limit`) — per-*user* rather
  than per-IP (every admin route is already authenticated, so the user
  id is a tighter key than a shared office/NAT IP) — not shared code
  with `app.ai.rate_limit`, a second small disclosed MVP rather than a
  premature shared abstraction for two callers (CLAUDE.md rule 12).
  `/api/v1/auth/*`, `/api/v1/tracking/*`, and `/api/v1/notifications/*`
  have no dedicated rate limiter either — a real gap for `/auth/login`
  specifically (credential-stuffing/brute-force exposure), noted here
  rather than silently left undocumented; considered but out of this
  work's scope (no rate-limiting infrastructure beyond the `/ai/*`/
  `/admin/*` MVPs exists to extend, and building a third bespoke
  limiter here would duplicate rather than generalize it — a job for
  whichever future phase builds real cross-route rate-limiting
  infrastructure).
- No dependency-scanning CI job exists yet (arrives with CI, Phase 1).
- No penetration test or formal security audit has been performed — that
  is Phase 15's deliverable, not something this document certifies.

## 15. Related Documents

- [PRIVACY.md](PRIVACY.md) — data minimization, consent, deletion, export
- [ADR-009](ADR/ADR-009-authentication-strategy.md) — authentication decision
- [AI_ARCHITECTURE.md](AI_ARCHITECTURE.md) §7 — AI safety/abuse detail
- [DATABASE.md](DATABASE.md) §2.7–§2.8 — provenance, change records, users/profiles
- [DATA_GOVERNANCE.md](DATA_GOVERNANCE.md) §8 — change control
- [DEPLOYMENT.md](DEPLOYMENT.md), [OBSERVABILITY.md](OBSERVABILITY.md) — operational topology (not defined here)
- [ROADMAP.md](ROADMAP.md) Phase 15 — hardening pass and acceptance criteria
