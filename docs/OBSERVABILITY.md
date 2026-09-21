# CivicLens — Observability Architecture

Defines how CivicLens will know it is working, know when it isn't, and know
whether the data it shows is still trustworthy. **No logging, monitoring, or
alerting infrastructure exists yet** — the project is in Phase 0. This is
the target design for when the API and ingestion pipeline exist
(Phases 1–13), hardened in [ROADMAP.md](ROADMAP.md) Phase 16. Toolset
choices are described generically (a structured logging library, a hosted
error-tracking service, a metrics/dashboarding stack) rather than naming
vendors — that selection is an implementation-time decision
([CLAUDE.md](../CLAUDE.md) rule 13), recorded via an ADR
([ADR/](ADR/README.md)) when made.

## 1. Principles

- **Serves the modular monolith, not a distributed system.** Per
  [ARCHITECTURE.md](ARCHITECTURE.md) §1, observability should not import
  microservices-grade complexity CivicLens doesn't have
  ([CLAUDE.md](../CLAUDE.md) rule 11).
- **Trust is observable.** Source freshness and AI groundedness are
  first-class metrics (§9, §7), not generic app monitoring afterthoughts.
- **Never log what must not leak** (§2).

## 2. Structured Logging

- All backend logs are structured (JSON or equivalent), emitted through
  one shared logging configuration across domain modules — no ad hoc
  `print`/string logs.
- **Correlation / request IDs** — every inbound request gets a request ID
  at the edge, attached to every log line for that request, and returned
  in the response, so a reported issue traces to its full log trail.
- Standard fields: timestamp, request ID, module, level, message, and
  (where applicable) authenticated user ID — not email/name — and the
  entity type/ID being acted on.
- **Must never be logged**: passwords/hashes, JWT/session tokens, API
  keys or provider credentials, full user profile payloads (age,
  qualification, income, category, domicile — [PRIVACY.md](PRIVACY.md)
  scope), raw AI prompts/responses containing user-identifying content,
  and full request/response bodies on authenticated endpoints by default
  (allow-list specific fields if needed, never log wholesale).
- Level discipline: `ERROR` for failures needing attention, `WARNING` for
  handled degradation (e.g. a source fetch retry), `INFO` for significant
  state transitions (publish, review approval, tracking subscription),
  `DEBUG` off in production by default.

## 3. Error Tracking

- **Backend** — unhandled exceptions and explicitly captured errors go to
  a centralized, hosted error-tracking service, tagged with the request
  ID (§2) so an error correlates back to its full log trail, originating
  module, and affected entity.
- **Frontend** — client errors (render errors, unhandled rejections,
  failed API calls past retry) report to the same service, tagged with
  route and a correlation identifier, PII scrubbed before transmission
  ([PRIVACY.md](PRIVACY.md)).
- A spike in error rate is an alerting condition (§11), not just a
  dashboard curiosity.

## 4. Metrics

Tracked per engine ([ARCHITECTURE.md](ARCHITECTURE.md) §5), since each has
a distinct failure mode:

| Engine | Key metrics |
|---|---|
| Civic Search | query latency (p50/p95), zero-result rate, index freshness lag |
| Civic AI | response latency, token cost per request, groundedness rate (sampled from the eval harness, [TESTING.md](TESTING.md) §AI evaluation), refusal rate, prompt-injection detection hits |
| Eligibility Engine | evaluation volume, `ELIGIBLE`/`NOT_ELIGIBLE`/`INCOMPLETE` distribution, evaluation latency (should be near-zero — a regression signals an external call creeping into the pure decision path) |
| Tracking & Alerts | notification delivery success/failure rate and latency from approval to delivery |
| Ingestion (Phase 13+) | see §8 |
| API (general) | request rate, error rate (4xx/5xx split), latency percentiles per route group |

Exported to a metrics/dashboarding stack (e.g. a Prometheus-compatible
collector + dashboards, or a hosted APM product — vendor TBD), organized
by engine to match the product's own structure.

## 5. Health Checks

- **Liveness** — `/health/live`: process is up, no dependency checks; used
  by the deployment platform to decide on restarts.
- **Readiness** — `/health/ready`: additionally checks PostgreSQL
  connectivity, reporting "not ready" so traffic stops routing to an
  instance that can't serve real requests, without killing it outright.
- Both are unauthenticated, minimal, and excluded from request-volume/
  error-rate dashboards so health-check polling doesn't skew engine
  metrics.

## 6. Request Tracing

CivicLens is a modular monolith, not a distributed system, so a full
distributed-tracing platform (cross-service spans, service maps) is
unjustified complexity now ([CLAUDE.md](../CLAUDE.md) rule 11):

- The request ID (§2) threads through every log line and error report for
  a request, giving end-to-end visibility within the one process without
  a separate tracing backend.
- Where a request has distinct internal stages worth timing separately
  (e.g. an AI request: intent parse → retrieval → context assembly → LLM
  call → response), lightweight in-process timing spans are logged
  against the same request ID, rather than adopting an OpenTelemetry-style
  distributed tracer.
- If a module is ever extracted into its own service
  ([ARCHITECTURE.md](ARCHITECTURE.md) §1, §11), that is the trigger to
  revisit this via a new ADR — not before.

## 7. AI Usage Monitoring

Addresses the rate-limiting/cost concern in
[AI_ARCHITECTURE.md](AI_ARCHITECTURE.md) §7:

- **Token/cost tracking** — every LLM call (via the provider abstraction,
  so vendor-agnostic) logs prompt/completion tokens and estimated cost,
  aggregated per user and system-wide, to catch both a single abusive user
  and aggregate cost drift.
- **Rate-limit observability** — AI-endpoint rate-limit rejections are
  counted separately from generic 4xx errors, so limit tuning is
  data-informed.
- **Groundedness-rate dashboard** — production responses are sampled and
  scored against the same groundedness/citation-accuracy criteria as the
  offline eval harness ([TESTING.md](TESTING.md) §AI evaluation), so a
  real-world drop is visible before it becomes a trust incident.
- Cost and groundedness dashboards are reviewed together — a cost-cutting
  change must not ship without confirming groundedness didn't regress.

## 8. Ingestion Monitoring

Once the pipeline exists (Phase 13, [DATA_SOURCES.md](DATA_SOURCES.md)
§3), each stage (`FETCH → EXTRACT → NORMALIZE → VALIDATE → CHANGE DETECT →
REVIEW → PUBLISH → INDEX`) is independently observable:

- Per-stage success/failure counts and latency, so a failure is
  attributable to a specific stage (e.g. EXTRACT breaking on a changed
  source layout), not a generic "ingestion broke."
- **Review-queue backlog size** — count and age distribution of items
  awaiting human review ([DATA_SOURCES.md](DATA_SOURCES.md) §4), tracked
  continuously; a growing backlog signals review capacity isn't keeping
  pace, which directly risks stale published data.
- Per-source health (last successful fetch, consecutive-failure count) so
  a source silently breaking is caught before a user reports stale data.

## 9. Source Freshness Monitoring

A first-class, product-differentiating operational concern unique to
CivicLens's trust model:

- A dashboard surfaces entities whose `verification_records.review_due_at`
  ([DATABASE.md](DATABASE.md) §2.7) is approaching (configurable lead
  time, e.g. 7/14 days), so review capacity is planned ahead of records
  going stale.
- A separate view surfaces entities already `NEEDS_REVIEW` or `EXPIRED`
  ([DATA_GOVERNANCE.md](DATA_GOVERNANCE.md) §4), broken down by domain and
  staleness age — these are showing a visible caveat to users right now
  and are top review-queue priority.
- Freshness metrics are tracked per domain and per state, so a problem
  concentrated in one area isn't averaged away system-wide.
- This is the operational counterpart to the "Last verified: DATE"
  product requirement ([PRODUCT_REQUIREMENTS.md](PRODUCT_REQUIREMENTS.md)
  NFR-T2) — how the team keeps that promise true at scale, not just at
  publish time.

## 10. Search Analytics

- Top queries and zero-result queries are logged and aggregated (query
  text, normalized — no linkage to a specific user's identity is needed
  or retained for this purpose).
- Used only to prioritize content coverage (a recurring zero-result query
  reveals a domain/state gap) and tune relevance
  ([TESTING.md](TESTING.md) §7) — **never** for ad targeting or profiling,
  consistent with [PRODUCT.md](PRODUCT.md) §6 and [PRIVACY.md](PRIVACY.md).
- Zero-result rate is also a standing metric (§4), reviewed alongside
  ingestion priorities.

## 11. Alerting

Conditions that page a human sooner than the next dashboard review:

- **Ingestion pipeline failures** — repeated fetch/extract/validate
  failures for a source, or the review-queue backlog (§8) crossing a
  defined size/age threshold.
- **Error-rate spikes** — backend or frontend error rate (§3) exceeding a
  baseline-relative threshold over a short window.
- **AI groundedness-rate drops** — the production groundedness dashboard
  (§7) falling below the accuracy bar set for the AI feature flag
  ([ROADMAP.md](ROADMAP.md) Phase 11) — a direct trust-risk signal.
- **Source freshness SLA breaches** — `NEEDS_REVIEW`/`EXPIRED` count (§9)
  exceeding a defined threshold, or backlog age for high-priority domains
  (e.g. time-critical recruitment notices,
  [DATA_SOURCES.md](DATA_SOURCES.md) §6) exceeding its SLA.
- **Health check failures** — readiness (§5) failing across instances,
  indicating a database connectivity problem.

Alert routing (who's paged, via what channel) is an operational runbook
detail decided at implementation time — this document defines the
conditions, not the on-call schedule.

## 12. Explicitly Not Built Yet

- Any logging configuration, error-tracking account, or metrics/
  dashboarding stack — none exists in Phase 0.
- The ingestion pipeline itself and its monitoring (§8) — target Phase 13.
- The AI pipeline itself and live groundedness/cost dashboards (§7) —
  target Phase 11.
- Any distributed tracing system — deferred indefinitely per §6 unless a
  documented module extraction creates a real need.
- Formal alert-routing/on-call tooling — conditions are defined here
  (§11); the paging mechanism is an implementation-time choice.
