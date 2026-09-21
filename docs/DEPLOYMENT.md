# CivicLens — Deployment

This document expands [ADR-010](ADR/ADR-010-deployment-architecture.md)
into a full operational deployment strategy: environments, pipeline shape,
infrastructure-as-code, secrets, migrations, backups, rollback, and
downtime posture. ADR-010 makes the core decisions (containerize both
apps, frontend on a platform built for it, backend on a managed container
platform, managed Postgres, no Kubernetes); this document does not
re-litigate them, only operationalizes them.

**Nothing in this document is provisioned yet.** No cloud account,
container registry, CI pipeline, or production database exists. This is
the target shape for [ROADMAP.md](ROADMAP.md) Phase 17 (Deployment +
Monitoring), and the promotion/environment model applies from the first
real deploy onward.

## 1. Environments and Promotion Flow

Three environments, in order: **local → staging → production**.

- **Local**: Docker Compose runs the FastAPI backend and PostgreSQL
  together (`infra/docker-compose.yml`, not yet created); the Next.js
  frontend runs natively for fast refresh, pointed at the local backend.
  No secrets beyond placeholder `.env` values ([CLAUDE.md](../CLAUDE.md)
  rule 15).
- **Staging**: mirrors production topology (same container image build,
  same platform choices) at lower scale, per [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md)
  §4.
- **Production**: serves real users.

**Promotion principle**: a single backend container image, built once per
change, is promoted unmodified from staging to production. The frontend
follows the equivalent model on its platform (the same build output
promoted, not rebuilt per environment). What differs between environments
is:

- Environment variables and secrets (database URL, LLM API key, JWT
  signing key, feature flag values) injected at deploy/runtime — never
  baked into the image.
- The data each environment's database holds.
- Which ingestion sources are live vs. sandboxed
  ([SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md) §4,
  [DATA_SOURCES.md](DATA_SOURCES.md) §2).

This "build once, promote the artifact" model is what makes a staging
verification meaningful — if staging passes, production is running
byte-identical application code, not a re-compiled variant.

## 2. CI/CD Pipeline Shape

Pipeline stages, run on every pull request and on merge to `main`:

```
LINT → TEST → BUILD → PUSH (image/artifact) → DEPLOY
```

| Stage | What runs | Gate |
|---|---|---|
| Lint | ESLint/Prettier (frontend), ruff/black (backend) | Must pass to merge |
| Test | Frontend unit/component tests, backend unit + integration tests (against an ephemeral CI Postgres), eligibility determinism suite, AI evaluation suite (once it exists) — see [TESTING.md](TESTING.md) | Must pass to merge |
| Build | Backend: build the Docker image. Frontend: platform-native build (e.g. the Vercel build step) | Must succeed |
| Push | Backend image pushed to a container registry, tagged with the commit SHA (and a moving `staging`/`latest` tag as appropriate) | N/A |
| Deploy — staging | Automatic on merge to `main`: new image deployed to staging, Alembic migrations run against the staging database (§5) | Auto-deploy, no manual approval |
| Deploy — production | **Requires explicit human approval** (a manual gate in the pipeline, e.g. a protected environment/approval step) after staging verification | Manual approval required |

Production deploys are never automatic on merge. A merge to `main` reaches
staging automatically; reaching production is a deliberate, approved
action referencing a specific staging-verified build. This matches the
project's phase-gated approach in [CLAUDE.md](../CLAUDE.md) (rule 22:
approval before major changes) applied to releases.

The frontend and backend can deploy independently (different release
cadences per ADR-010's consequences), but a backend API change that the
frontend depends on should be verified in staging together before either
is promoted to production — this is a release-process discipline, not an
enforced technical coupling.

## 3. Infrastructure as Code

Keep this as simple as the platform allows, consistent with [CLAUDE.md](../CLAUDE.md)
rule 11 (no unjustified complexity):

- Prefer the chosen platform's **native config-as-code** (e.g., a Fly.io
  `fly.toml`, a Render `render.yaml`/Blueprint, or equivalent) for the
  backend container service, checked into `infra/`.
- Use **Terraform** only for pieces that genuinely need declarative,
  versioned, multi-resource orchestration (e.g., DNS, a managed Postgres
  instance plus its network/firewall rules, a CDN configuration) — not as
  a mandatory layer over every platform setting the platform's own config
  format already covers well.
- Do not introduce a general-purpose orchestration or config-management
  tool (Ansible, Pulumi, custom scripts duplicating platform features)
  without a documented reason, per the same "avoid unnecessary
  dependencies" rule.
- Whatever tool is used, infrastructure definitions live in `infra/` in
  the monorepo and go through the same PR review as application code —
  infrastructure changes are not made by hand in a provider console for
  anything beyond one-off diagnosis.
- Final vendor selection (which container platform, which managed Postgres
  provider, which registry) is made when Phase 17 actually begins, not
  fixed here — ADR-010 deliberately leaves this open. Whatever is chosen,
  this document's environment/pipeline/rollback shape applies unchanged.

## 4. Secrets Management

Production and staging secrets (database credentials, JWT signing keys,
LLM provider API keys, OAuth client secrets) are held in **the platform's
native secret store** (e.g., Fly.io secrets, Render environment groups, AWS
Secrets Manager) or a dedicated secrets manager if the chosen platform
lacks one — never in the repository, never in a Dockerfile, never in a
committed `.env` file.

This directly enforces [CLAUDE.md](../CLAUDE.md):
- Rule 14 — never expose secrets in code, logs, or commit history.
- Rule 15 — never commit `.env` files with real values; only
  `.env.example` with placeholders is committed, for every environment.

Practical rules:
- Secrets are injected as environment variables at container start, read
  once at app boot via the settings module (per ADR-003's Pydantic
  settings pattern).
- Local development secrets (e.g., a throwaway local LLM key, if any) stay
  in an untracked local `.env`, never shared through the repo.
- Rotating a secret is a platform-console/API action followed by a
  redeploy or restart — it does not require a code change.
- CI needs its own scoped secrets (registry push credentials, staging
  deploy token) held in the CI provider's secret store, with production
  deploy credentials gated behind the manual-approval step in §2.

## 5. Database Migration Strategy in Deployment

Migrations (Alembic, per ADR-003) are a **controlled, explicit pre-deploy
step** — never something the application runs automatically on every boot.
Running migrations on every container start is rejected because it makes
migration execution non-deterministic with respect to deploy ordering
(multiple instances starting concurrently could race) and hides schema
changes inside application logs instead of a visible pipeline step.

Target sequence for a deploy that includes a migration:

1. CI builds and pushes the new image (§2).
2. As an explicit pipeline step (not inside the app container's normal
   startup), Alembic `upgrade head` runs against the target environment's
   database, using a short-lived migration job/task, before traffic is
   shifted to the new image.
3. Only after migrations succeed does the deploy proceed to roll out the
   new application containers.
4. If migration fails, the deploy stops before any new application code is
   live — the previous container version keeps serving on the
   pre-migration schema.

Every migration must have a working `downgrade` ([CLAUDE.md](../CLAUDE.md)
rule 17) specifically so that step 4's failure path, and any rollback
(§7), has a real reverse migration to run rather than a manual hotfix.
Additive, backward-compatible migrations (new nullable column, new table)
are preferred over breaking changes, so that a brief window where old code
and new schema coexist (or vice versa) never breaks the running
application — this is what makes low-downtime deploys (§8) safe with a
migration in the mix.

## 6. Backup and Disaster Recovery (PostgreSQL)

Relies on the managed Postgres provider's built-in capabilities rather
than a custom backup system, consistent with choosing a managed database
in the first place (ADR-004, ADR-010):

- **Automated backups**: daily automated snapshots at minimum, retained
  per the provider's configurable retention window (exact window is a
  Phase 17 configuration decision, not fixed here).
- **Point-in-time recovery (PITR)**: enabled via the managed provider's
  PITR/WAL-archiving feature, allowing restore to a specific timestamp
  (not just the last daily snapshot) — this is the primary protection
  against a bad publish or an operational mistake, not just full outages.
- **Restore drill**: a documented, periodically-rehearsed procedure —
  restore the latest backup (or a PITR point) into a fresh, isolated
  database instance and verify the application can boot against it and
  key read queries return expected data. This drill must be actually
  performed (not just documented) before Phase 17's acceptance criteria
  ("a tested rollback procedure," [ROADMAP.md](ROADMAP.md) Phase 17) are
  considered met, and re-run periodically thereafter (cadence set when
  operational).
- **Scope**: backup/DR covers the single PostgreSQL database, which is the
  sole system of record (ADR-004) — there is no secondary datastore to
  separately back up at this phase.

## 7. Rollback Procedure

Rollback is **redeploying the previous known-good container image** —
never editing forward on a broken production deploy under pressure.

1. Identify the last known-good image tag (the commit SHA tag from §2's
   push stage).
2. Redeploy that image to production via the same deploy mechanism used
   for forward deploys (not a special-cased manual process).
3. **If the broken deploy included a migration**: run the corresponding
   Alembic `downgrade` before or as part of the rollback, so the schema
   matches what the rolled-back application code expects. This is exactly
   why every migration needs a working `downgrade` ([CLAUDE.md](../CLAUDE.md)
   rule 17) — rollback is the scenario that rule exists for.
4. If the broken deploy did not touch the schema, rollback is
   image-redeploy only, with no database action.
5. Verify via the same smoke checks used post-deploy (§8) before
   considering the incident resolved.

Because migrations are designed to be additive/backward-compatible where
practical (§5), most rollbacks do not require a downgrade at all — the old
code simply ignores a new nullable column. The downgrade path exists for
the cases where that isn't possible.

## 8. Low-Downtime Deployment

- **Backend**: the managed container platform performs a rolling
  replace — new containers are started and pass a health check
  (`/health`, per [ROADMAP.md](ROADMAP.md) Phase 2) before old containers
  are terminated and traffic is shifted. A deploy is never a hard
  stop-then-start of the only running instance.
- **Frontend**: the frontend platform's native deployment model (e.g.,
  Vercel's atomic deploys with instant rollback to a previous build)
  provides zero-downtime deploys by construction — a new deployment is
  fully built and only then atomically swapped in.
- **Database schema changes**: kept backward-compatible during the
  window between migration and full rollout (§5), so old and new
  application code can both run correctly against the post-migration
  schema during a rolling deploy.
- This is a low-downtime posture appropriate to a single-region,
  single-backend-service deployment — it is not a claim of
  multi-region/active-active high availability, which is out of scope
  at this phase.

## 9. Monitoring Hook-In

Deployment emits into, but does not define, the observability stack.
Every deploy should be visible as an event correlated with metrics/error
rates (e.g., a deploy marker on dashboards) so a regression right after a
release is immediately attributable. Full monitoring, alerting, logging,
and on-call/dashboard design is specified in
**[OBSERVABILITY.md](OBSERVABILITY.md)** — this document only asserts that
deployment must integrate with it (health checks, deploy markers, and
post-deploy smoke checks feeding into it), not redefine it.

## 10. Explicitly Not Built Yet

- No cloud/platform accounts, container registry, or CI pipeline exist.
- No `infra/` IaC files, Dockerfiles, or Compose files exist.
- No production or staging database is provisioned.
- No secrets manager is configured; no real secrets exist anywhere.
- No backup/restore drill has been performed (there is nothing to back up
  yet).
- Final vendor selection (container platform, managed Postgres provider,
  registry, secrets manager) is deferred to Phase 17.

## 11. Related Documents

- [ADR-010](ADR/ADR-010-deployment-architecture.md) — the accepted decision
  this document expands
- [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md) — runtime topology and
  environment differences this pipeline deploys
- [OBSERVABILITY.md](OBSERVABILITY.md) — monitoring, alerting, logging
- [TESTING.md](TESTING.md) — what the CI test stage actually runs
- [SECURITY.md](SECURITY.md) — secrets and access-control detail beyond
  §4's deployment-specific summary
- [CLAUDE.md](../CLAUDE.md) — rules 14, 15, 17 enforced throughout this
  document
- [ROADMAP.md](ROADMAP.md) Phase 17 — when this document's target state is
  actually implemented
