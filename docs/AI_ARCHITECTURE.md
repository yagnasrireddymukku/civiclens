# CivicLens — AI / RAG Architecture

Governing principle (see [DATA_GOVERNANCE.md](DATA_GOVERNANCE.md)): **the
LLM is never the source of truth.** Civic AI explains and synthesizes
verified structured data; it does not originate facts, dates, eligibility
verdicts, or official information.

## 1. Pipeline

```
USER QUERY
   ↓
INTENT / QUERY ANALYSIS      (what is being asked; which domain/entities)
   ↓
RETRIEVAL                     (structured DB + search index + approved docs)
   ↓
STRUCTURED DATABASE + SEARCH + APPROVED DOCUMENTS
   ↓
CONTEXT ASSEMBLY               (assemble grounded context + citations)
   ↓
LLM                            (provider-abstracted; synthesis only)
   ↓
SOURCE-CITED RESPONSE
   ↓
USER
```

## 2. Intent / Query Analysis

Classifies the query into: domain (jobs/exams/schemes/services/
scholarships/representatives/elections/documents/eligibility/general),
entity mentions (state, district, qualification, age, etc.), and query type
(lookup, eligibility question, explanation request, comparison). This can
start as a lightweight classifier/LLM-assisted parse; it must produce a
structured intent object that drives retrieval — not free-text straight to
the LLM.

## 3. Retrieval

Two complementary retrieval paths, combined:

1. **Structured retrieval** — direct queries against domain tables filtered
   by the parsed intent (state, category, status, date range). This is the
   primary path for factual questions ("when is the TSPSC group 2 exam").
2. **Semantic retrieval** — `pgvector` similarity search over an
   `embeddings` table (entity_type, entity_id, chunk, vector) built from
   published, verified structured data and approved supporting documents
   (e.g., official notification text where licensing permits storage).
   Used for natural-language and exploratory questions.

Only `VERIFIED` (and, with a visible caveat, `NEEDS_REVIEW`) records are
eligible for retrieval. `UNVERIFIED` or `EXPIRED` records are excluded from
grounding context by default (see
[DATA_GOVERNANCE.md](DATA_GOVERNANCE.md) §4).

## 4. Context Assembly

Assembled context includes, per retrieved fact: the fact itself, its
source citation (title + URL + last-verified date), and its verification
status. The prompt sent to the LLM explicitly separates "grounded context"
from "instructions," and instructs the model to:

- answer only from the provided context
- cite the source for every factual claim
- state explicitly when the context does not contain an answer, rather
  than filling the gap
- never issue an eligibility determination — defer to the Eligibility
  Engine ([ELIGIBILITY_ENGINE.md](ELIGIBILITY_ENGINE.md)) and, if asked,
  explain the engine's rule-by-rule result rather than compute its own

## 5. LLM Layer — Provider Abstraction

A thin interface (e.g., `LLMProvider.complete(prompt, context) -> response`)
decouples the application from any single vendor. Provider selection
(Anthropic, OpenAI, or others) is a configuration/infrastructure decision,
not a product-code dependency — no module outside this abstraction imports
a vendor SDK directly. This enables provider swaps, multi-provider
fallback, and cost/quality tuning without touching calling code. See
[ADR-006](ADR/ADR-006-ai-rag-architecture.md).

System-prompt-level constraints enforced regardless of provider:
- No persuasive or comparative political framing (see
  [DATA_GOVERNANCE.md](DATA_GOVERNANCE.md) §5).
- No fabrication of URLs, dates, or figures not present in context.
- No medical/legal/financial advice beyond what the grounded content states.

## 6. Response Contract

Every Civic AI response is structured, not free text alone:
- `answer` — synthesized explanation
- `citations[]` — source records used, each with URL, title, last-verified
  date, and verification status
- `confidence` / `grounding_status` — whether the answer is fully grounded,
  partially grounded, or ungrounded (in which case the UI must show an
  explicit "we couldn't verify this" state rather than the raw answer)

## 7. Safety & Abuse Considerations

- **Prompt injection**: retrieved content (including future ingested
  documents) is treated as data, not instructions; the system prompt is
  structurally separated from retrieved/user content. See
  [SECURITY.md](SECURITY.md) §AI.
- **Data isolation**: a user's personal profile data is only included in
  context for that user's own authenticated request, never used to answer
  another user's query, and never used to train or fine-tune a model.
- **Rate limiting & cost control**: AI endpoints are rate-limited per user
  and monitored for cost/usage (see [OBSERVABILITY.md](OBSERVABILITY.md)
  §AI usage monitoring).

## 8. Evaluation

AI responses are evaluated (see [TESTING.md](TESTING.md) §AI evaluation)
against:
- **Groundedness** — every factual claim traces to a citation
- **Citation accuracy** — citations actually support the claim made
- **Refusal correctness** — the system says "I don't know" when context is
  insufficient, instead of guessing
- **Neutrality** — no persuasive political framing leaks through

## 9. Explicitly Not Built Yet

- Any live LLM integration or API key configuration
- Any embeddings/vector index population
- Any prompt templates beyond the constraints documented here

This document defines the target shape for Phase 11 (Civic AI + RAG).
