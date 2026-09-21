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
