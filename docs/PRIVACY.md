# CivicLens — Privacy Architecture

Companion to [SECURITY.md](SECURITY.md). Defines how CivicLens collects,
uses, retains, and lets users control their own data. Implements
[PRODUCT_REQUIREMENTS.md](PRODUCT_REQUIREMENTS.md) §2.4 (NFR-PRIV1–PRIV-n):
**no collection of sensitive personal data without a named product
requirement it serves.**

**No application code exists yet.** This is target design for the
account/personalization features starting in Phase 3
([DATABASE.md](DATABASE.md) — `users`/`profiles`) and the formal privacy
hardening pass in Phase 15 (§8, [ROADMAP.md](ROADMAP.md) Phase 15).

This document describes an architecture designed to align with
data-minimization and consent principles consistent with applicable
Indian privacy law. It does not certify legal compliance with any
specific statute — a dedicated legal compliance review is a named future
task (tracked against Phase 15), not something this document performs.

## 1. Data Minimization Principle

CivicLens collects only what a **named, documented feature** needs;
nothing is inferred about a user beyond what they explicitly provide. The
`profiles` table ([DATABASE.md](DATABASE.md) §2.8) is the concrete example:

- Fields — age/DOB, qualification, state/district, category — each exist
  because [PRODUCT_REQUIREMENTS.md](PRODUCT_REQUIREMENTS.md) FR-E1/FR-P2
  names a specific use (eligibility matching, personalized dashboard).
- Every `profiles` field is **optional**; core search/browse/eligibility
  features work with zero profile data.
- Nothing is derived from behavior (clickstream, device fingerprinting)
  and stored as an inferred attribute. `saved_items`/`tracking_items`
  record explicit user actions, not an inferred interest profile.
- A new `users`/`profiles` field requires a traced requirement in
  [PRODUCT_REQUIREMENTS.md](PRODUCT_REQUIREMENTS.md), same as
  [DATABASE.md](DATABASE.md) §0's rule for any table, with extra weight
  for personal data.

## 2. What CivicLens Does Not Collect

- No sensitive-category data (religion, caste, disability, health,
  biometrics) **unless** a specific, named eligibility rule requires it —
  e.g., **reservation category**, which some government jobs/schemes
  legitimately condition on. Even then: collected only because
  [ELIGIBILITY_ENGINE.md](ELIGIBILITY_ENGINE.md) needs it for a real,
  sourced rule ([DATA_GOVERNANCE.md](DATA_GOVERNANCE.md)); kept out of
  logs and generic analytics; scoped to the eligibility flow, not
  broadcast to every profile-consuming feature.
- No location tracking beyond a user-entered state/district — no GPS,
  IP-geolocation inference, or continuous tracking.
- No behavioral-advertising data, ad-tracking pixels, or cross-site
  tracking identifiers ([PRODUCT.md](PRODUCT.md) §6).
- No inferred political preference ([DATA_GOVERNANCE.md](DATA_GOVERNANCE.md)
  §5) — a user may read about representatives/elections; CivicLens never
  records that as a preference signal.
- No collection of another named person's sensitive data through the
  product.

## 3. Consent

- **Baseline account data** (email, password/OAuth identity, role):
  consent is implicit in account creation — the minimum needed to operate
  an account at all.
- **Optional data and communications** require **explicit, opt-in**
  consent, separable from account creation:
  - Any `profiles` field beyond account basics — opted into to unlock
    eligibility/personalization, declinable.
  - Email notifications (`notifications`,
    [DATABASE.md](DATABASE.md) §2.8) — opt-in, with working opt-out on
    every email and in settings. SMS/WhatsApp is out of scope for v1
    ([PRODUCT_REQUIREMENTS.md](PRODUCT_REQUIREMENTS.md) §3) and would need
    its own consent flow if introduced.
  - Any sensitive-category field (§2) requires a distinct consent step
    naming exactly why it's needed and which feature uses it — never
    bundled into general terms.
- Withdrawing consent (disabling notifications, clearing an optional
  field) is as easy as granting it and takes effect immediately.

## 4. Account Deletion

Two categories, in tension:

- **User-owned, non-shared data** — `profiles`, `saved_items`,
  `tracking_items`, undelivered `notifications`
  ([DATABASE.md](DATABASE.md) §2.8) — is **hard-deleted**, consistent with
  [DATABASE.md](DATABASE.md) §0 rule 3.
- **Records referencing the user's actions that serve system integrity** —
  audit/access logs and `change_records`/`verification_records` entries
  where the user acted as `editor`/`admin` reviewer
  ([DATABASE.md](DATABASE.md) §2.7, [SECURITY.md](SECURITY.md) §9) — are
  **anonymized, not deleted**: the actor reference becomes a stable
  non-identifying marker while the fact, timing, and content of the
  review is preserved.
- **The tension**: account deletion is a privacy right; deleting the
  record of what was reviewed/approved would break the audit trail that
  makes public-data changes traceable
  ([DATA_GOVERNANCE.md](DATA_GOVERNANCE.md) §8, NFR-A1 in
  [PRODUCT_REQUIREMENTS.md](PRODUCT_REQUIREMENTS.md) §2.3).
- **Resolution**: keep the *event*, drop the *identity*. An anonymized
  `change_record` still answers "was this reviewed, when, does it trace to
  a source" without answering "by whom." The same pattern applies to
  auth audit logs: retained for the normal investigation window (§6), then
  unlinked from the deleted account.
- Deletion is one-way, preceded by confirmation; a short grace period to
  allow undo is acceptable, but is not a place to retain data indefinitely.

## 5. Data Export

- Scope: `users` fields (excluding password hash), all `profiles` fields,
  `saved_items`, `tracking_items`, `notifications` — the §4 "user-owned"
  set.
- Format: structured JSON, generated on request, not pre-built.
- Contains only the requesting user's own data, even where a foreign key
  touches something shared (e.g., a `tracking_item` references a public
  job by id, not by embedding another user's data).
- Read-only; no side effects on the account.

## 6. Retention Policy

- **Active accounts**: retained while the account exists and relevant
  consent (§3) stands.
- **Inactive accounts**: an account with no login activity for an
  extended period (threshold set at Phase 15 from real usage, not
  invented here) is a candidate for a re-consent prompt before eventual
  deletion — data is not kept indefinitely by default.
- **Notifications**: delivered/read notifications are kept only long
  enough to be useful in the dashboard, then eligible for deletion.
- **Audit/access logs**: bounded investigation window
  ([SECURITY.md](SECURITY.md) §9), then deleted or anonymized per §4.
- **Public domain data** (jobs, schemes, representatives) is governed by
  [DATA_GOVERNANCE.md](DATA_GOVERNANCE.md)/[DATABASE.md](DATABASE.md)
  soft-delete rules, not this document — it isn't personal data.

## 7. Children / Minors

CivicLens is not designed or marketed for children; account creation
implies the user is old enough to hold a government-services account in
their own right. No age-verification beyond the self-reported, optional
`age`/DOB field ([DATABASE.md](DATABASE.md) §2.8) is planned. This is
noted as an open consideration: if a future phase specifically targets
younger students as a named requirement, this section must be revisited
with an explicit parental-consent design before that feature ships — not
improvised inside an unrelated PR.

## 8. Privacy and the AI Layer

Detail lives in [AI_ARCHITECTURE.md](AI_ARCHITECTURE.md) §7; referenced,
not duplicated:

- A user's `profiles` data enters an LLM's context only for that user's
  own authenticated session.
- It is never used to answer another user's query and never used to
  train/fine-tune any model.
- Retrieved civic-data content is treated as data, not instructions
  ([SECURITY.md](SECURITY.md) §11), which also blocks a prompt-injection
  path that could otherwise try to exfiltrate another user's context.
- Conversation content is held to the same minimization discipline (§1):
  used to serve that session, not repurposed as a hidden behavioral
  profile. If a future phase persists multi-turn chat history, that
  persistence is itself a named requirement subject to this document's
  consent (§3), export (§5), and deletion (§4) rules.

## 9. Acceptance Criteria (Phase 15)

[ROADMAP.md](ROADMAP.md) Phase 15 names "account deletion/export verified
end-to-end" as acceptance criteria:

- [ ] Deletion hard-deletes `profiles`/`saved_items`/`tracking_items`/
      `notifications` while anonymizing (not deleting) any
      `change_records`/audit entries referencing past `editor`/`admin`
      actions (§4).
- [ ] Export returns a complete, correctly-scoped copy of a user's own
      data (§5), containing no other user's data.
- [ ] Every optional field/communication channel (§3) has an independent
      opt-in/opt-out taking effect immediately.
- [ ] No sensitive-category field exists without a documented, named
      eligibility-rule justification (§2), checked against the live
      `profiles`/`eligibility_conditions` schema.
- [ ] Retention rules (§6) run as scheduled jobs or documented manual
      processes.
- [ ] A test verifies one user's profile data is absent from another
      user's AI session context ([TESTING.md](TESTING.md) §AI evaluation).

## 10. Explicitly Not Built Yet

- No `users`/`profiles` tables exist yet (Phase 3).
- No account settings UI, deletion flow, or export endpoint exists yet.
- No consent-management UI or audit-log anonymization job exists yet.
- No legal compliance review against a specific Indian data-protection
  statute has been performed — see the scope note above; that review is a
  named future task, not something this document certifies.

## 11. Related Documents

- [SECURITY.md](SECURITY.md) — authentication, RBAC, audit logging mechanisms
- [DATABASE.md](DATABASE.md) §2.8 — `users`/`profiles`/`saved_items`/`tracking_items`/`notifications` schema
- [DATA_GOVERNANCE.md](DATA_GOVERNANCE.md) §8 — `change_records` audit trail this document's anonymization rule preserves
- [AI_ARCHITECTURE.md](AI_ARCHITECTURE.md) §7 — AI data isolation detail
- [PRODUCT_REQUIREMENTS.md](PRODUCT_REQUIREMENTS.md) §2.4 — governing NFRs
- [ROADMAP.md](ROADMAP.md) Phase 15 — acceptance criteria and hardening pass
