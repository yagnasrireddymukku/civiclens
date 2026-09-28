# CivicLens — Eligibility Engine Architecture

The Eligibility Engine is deterministic and rule-based. **The LLM is never
in the eligibility decision path** — it may explain a result the engine
already produced, but it cannot compute one (see
[AI_ARCHITECTURE.md](AI_ARCHITECTURE.md) §4, §6, and
[DATA_GOVERNANCE.md](DATA_GOVERNANCE.md)).

## 1. Strict Separation of Concerns

| Concern | Where it lives | Notes |
|---|---|---|
| User attributes | `profiles` (explicit, user-provided) | Never inferred; see [PRIVACY.md](PRIVACY.md) |
| Eligibility rules | `eligibility_rules` / `eligibility_conditions` | Sourced from an authoritative notification, carries `source_id` |
| Rule evaluation | Pure function in the `eligibility` module | No side effects, no external calls, fully unit-testable |
| Explanation | Generated from the evaluation trace (§4) — optionally phrased by the AI layer, but only from that trace | Never a new judgment |
| Official source | `sources` via the rule's `source_id` | Always shown alongside a result |

## 2. Data Model (see [DATABASE.md](DATABASE.md) §2.4 for full schema)

- `eligibility_rules(id, entity_type, entity_id, source_id, effective_date)`
  — a rule set that applies to one job/scheme/scholarship/service.
- `eligibility_conditions(id, rule_id, attribute, operator, value)` — an
  individual condition, e.g. `attribute=age, operator=between,
  value=[21,42]` or `attribute=qualification, operator=in,
  value=["B.Tech","B.E"]`.

Supported attributes are an explicit, versioned enum (age, date_of_birth,
qualification, category/reservation, domicile_state_id, domicile_district_id,
income_annual, gender, experience_years, ...) — extended deliberately, not
ad hoc, since every new attribute must map to something `profiles` can
actually collect.

## 3. Evaluation Semantics

Evaluation is a pure function:

```
evaluate(rule: EligibilityRule, attributes: UserAttributes) -> EligibilityResult
```

Rules:
- Every condition in a rule is evaluated independently against the
  provided attributes.
- If a required attribute is missing from the user's input, that condition
  evaluates to `UNKNOWN` (not `PASS` and not `FAIL`) — the engine must never
  assume a default value for a missing attribute that would change the
  outcome.
- The overall result is `ELIGIBLE` only if all conditions are `PASS`.
  `NOT_ELIGIBLE` if any condition is definitively `FAIL`. Otherwise
  `INCOMPLETE` (one or more `UNKNOWN`s, no `FAIL`s) — the UI prompts the
  user for the missing attribute rather than guessing.
- Operators are a fixed, tested set (`eq`, `neq`, `gte`, `lte`, `between`,
  `in`, `not_in`) — no free-form expression evaluation (no `eval`, no
  arbitrary code execution) — this keeps the engine auditable and safe.

## 4. Explanation / Evaluation Trace

Every evaluation returns a trace, not just a verdict:

```json
{
  "result": "INCOMPLETE",
  "conditions": [
    {"attribute": "age", "operator": "between", "value": [21, 42], "userValue": 23, "status": "PASS"},
    {"attribute": "qualification", "operator": "in", "value": ["B.Tech","B.E"], "userValue": "B.Tech", "status": "PASS"},
    {"attribute": "domicile_state_id", "operator": "eq", "value": "AP", "userValue": null, "status": "UNKNOWN"}
  ],
  "source": {"title": "...", "url": "...", "lastVerified": "2026-08-01"}
}
```

The frontend and the AI layer both render from this trace. The AI layer may
phrase it in natural language ("You meet the age and qualification
requirements; we need your domicile state to check the last condition") but
must not alter the verdict or add conditions not present in the trace.

## 5. Versioning & Effective Dates

Eligibility criteria for a recurring exam/scheme can change year to year.
`eligibility_rules.effective_date` and a link to the specific
`job_notification`/scheme version ensures a user is always evaluated
against the criteria for the specific opportunity instance they're viewing,
not a stale or unrelated rule set.

## 6. Testing Requirement

Deterministic test cases are **mandatory**, not optional (see
[TESTING.md](TESTING.md) §eligibility). Every operator and every
PASS/FAIL/UNKNOWN branch must have a unit test with fixed input/output
pairs using clearly-fictional fixture data
([DATA_GOVERNANCE.md](DATA_GOVERNANCE.md) §7).

## 7. Explicitly Out of Scope

- Fuzzy/probabilistic eligibility scoring ("70% likely eligible") — the
  engine deals in PASS/FAIL/UNKNOWN, not confidence percentages.
- Any eligibility computation performed by calling an LLM.
- Auto-applying on a user's behalf (this is a "check and explain" engine,
  not an application-automation engine, at v1).

## 8. Phase 11 Implementation Notes (Realized)

This document's §1–§7 above described the target design before an
implementation existed; this section records where the real
implementation (`apps/api/app/eligibility/`) landed, and the deliberate
narrowings from the original sketch. Full architectural rationale lives
in [DATABASE.md](DATABASE.md) §15; this section summarizes it from the
evaluation-semantics angle §1–§7 already established.

- **Entity reference**: `eligibility_rules` carries three nullable FKs
  (`job_id`/`scheme_id`/`service_id`, `CHECK` exactly one set) instead of
  §2's `entity_type`/`entity_id` polymorphic pair — real referential
  integrity for a fixed, small entity-type set. Scholarships are
  evaluated via their parent `scheme_id`, matching their status as a
  `Scheme` specialization ([DATABASE.md](DATABASE.md) §13), not a fourth
  entity type.
- **Attribute enum, finalized**: `AGE`, `INCOME_ANNUAL`,
  `EDUCATION_LEVEL`, `ACADEMIC_PERCENTAGE`, `ACADEMIC_CGPA`,
  `RESIDENCE_STATE`, `CATEGORY` — a subset of §2's illustrative list.
  `qualification`/`gender`/`experience_years` were not implemented: real
  qualification wording rarely reduces to one structured value (the same
  reasoning `Job.qualification_summary` already documents), and no
  documented product requirement named gender or experience as
  evaluation criteria for this phase. **Date windows are explicitly not
  an attribute** — an application window is a fact about the
  opportunity, already shown on its own detail page, not a question
  asked of the applicant.
- **Operators, exactly as specified**: `EQ`, `NEQ`, `GTE`, `LTE`,
  `BETWEEN`, `IN`, `NOT_IN` — §3's fixed set, unchanged. `BETWEEN` is
  inclusive on both bounds (documented and unit-tested at both
  boundaries).
- **Evaluation is stateless, not `Profile`-backed.** §1's table listed
  `profiles` as where "user attributes" live. No authentication module
  exists yet (Phase 3 built identity storage only), so there is no
  session to load a persisted profile from — `POST
  /api/v1/eligibility/evaluate` takes answers directly in the request
  body instead, evaluates them, and never persists them. A future
  authenticated flow could pre-fill this form from `Profile` fields
  without any change to the pure evaluation core.
- **Evaluability gate, stricter than every other domain's visibility
  rule**: only `verification_status == VERIFIED` rules are evaluated
  (not `NEEDS_REVIEW`) — §6's "no engine hardcodes an assumption that
  unverified data is safe to act on" principle, made concrete.
- **Versioning**: `EligibilityRule.rule_version` is a plain incrementing
  integer on an otherwise-immutable published row — simpler than §5's
  implied temporal history, sufficient because no rule-authoring/
  superseding admin workflow exists yet (matching every other domain's
  fixture-only-authoring stage).
- **Test matrix**: 100% branch coverage achieved on
  `app.eligibility.evaluator.evaluate_rule` (37 dedicated pure unit
  tests, `pytest --cov-branch`), satisfying §6's mandatory gate.
