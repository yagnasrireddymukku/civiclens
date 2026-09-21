# ADR-007: Eligibility Engine Architecture

## Status
Accepted

## Context
Eligibility determinations are consequential to users (whether they should
spend time/money applying to something) and must be reproducible, testable,
and never subject to LLM variability or hallucination.

## Decision
Implement eligibility as a **deterministic rule engine** operating over
explicit `eligibility_rules`/`eligibility_conditions` data and
user-provided `profiles` attributes, with a fixed set of comparison
operators and no code/expression evaluation. Full design in
[ELIGIBILITY_ENGINE.md](../ELIGIBILITY_ENGINE.md). The LLM may narrate a
result; it never computes one.

## Alternatives Considered
- **LLM-based eligibility reasoning** (ask the model "is this user
  eligible?"): rejected outright — non-deterministic, unauditable, and
  directly violates the source-of-truth doctrine
  ([DATA_GOVERNANCE.md](../DATA_GOVERNANCE.md)).
- **General-purpose rules engine (e.g., a Drools-style DSL or embedded
  scripting)**: rejected — a fixed operator set over typed attributes is
  sufficient for the eligibility criteria seen in government
  jobs/schemes/scholarships, and avoids the security/complexity surface of
  an embedded expression language ([CLAUDE.md](../../CLAUDE.md): avoid
  unnecessary dependencies).
- **Third-party eligibility/decisioning SaaS**: rejected — this is core,
  differentiating product logic tied tightly to India-specific civic rules;
  outsourcing it would both cost more and reduce control over correctness.

## Consequences
- Every eligibility attribute must be explicitly modeled before it can be
  used in a rule — extending the engine requires deliberate schema
  additions, not ad hoc rule text.
- Missing user data produces `UNKNOWN`/`INCOMPLETE`, never a guessed
  default — this is a correctness-over-completeness tradeoff by design.
- Full unit-test coverage of the evaluation function is mandatory
  ([TESTING.md](../TESTING.md) §eligibility) since this logic is the most
  consequential deterministic component in the system.
