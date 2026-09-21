# ADR-006: AI / RAG Architecture

## Status
Accepted

## Context
Civic AI must answer natural-language questions with source-backed,
non-hallucinated responses, per [DATA_GOVERNANCE.md](../DATA_GOVERNANCE.md).
It must not be locked to a single LLM vendor long-term.

## Decision
Build a retrieval-augmented generation pipeline
(see [AI_ARCHITECTURE.md](../AI_ARCHITECTURE.md)) where retrieval is
grounded in Postgres structured data + `pgvector` embeddings, and the LLM
call goes through a **provider-abstraction interface** so no application
code depends directly on a vendor SDK. Provider choice is a configuration
concern, made and revisited independently of this ADR.

## Alternatives Considered
- **Direct vendor SDK integration with no abstraction**: rejected — creates
  vendor lock-in and makes provider comparison/fallback/cost optimization
  require an application rewrite instead of a config change.
- **Fine-tuning a model on civic data**: rejected for v1 — RAG keeps facts
  in an auditable, updatable structured store rather than baked into model
  weights, which is essential given how frequently civic information
  changes (deadlines, schemes) and the zero-tolerance for stale/incorrect
  facts.
- **Separate vector database**: see [ADR-004](ADR-004-postgresql.md) —
  deferred in favor of `pgvector`.

## Consequences
- Every AI response must be traceable to retrieved context; the response
  contract ([AI_ARCHITECTURE.md](../AI_ARCHITECTURE.md) §6) requires
  citations and a groundedness indicator.
- Swapping or adding LLM providers is a configuration/infrastructure
  change, not an application-code change.
- Evaluation harness ([TESTING.md](../TESTING.md) §AI evaluation) is
  provider-agnostic since it tests the pipeline's grounding behavior, not a
  specific model's output.
