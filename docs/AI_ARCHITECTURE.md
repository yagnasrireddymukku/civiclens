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

- A dedicated intent/query-classification step (§2's sketch) — see §10
  for what retrieval actually does instead.
- A live, paid-tier evaluation of real answer quality against real
  government content (no real government data exists yet; only
  fixture-grounded groundedness/citation-integrity tests exist).
- Multi-turn conversation memory/history (every question is answered
  independently; no session-scoped chat history is persisted, per this
  phase's explicit "no fabricated chat history" instruction).
- Query-classification-driven structured filtering (state/category/date
  as a distinct retrieval path) — folded into the lexical path's
  existing filters instead of a separate intent layer.

## 10. Phase 12 Implementation Notes (Realized)

§1–§8 above described the target design before an implementation
existed. This section records where the real implementation
(`apps/api/app/ai/`) landed, and every deliberate deviation from that
original sketch. Full schema rationale lives in
[DATABASE.md](DATABASE.md) §16; this section summarizes it from the
pipeline/safety angle §1–§8 already established.

**No intent-classification step (§2).** Retrieval works directly off the
question text via the lexical and semantic paths below — no separate
LLM-assisted or rule-based query parser exists. This is a deliberate
scope narrowing, not an oversight: a real classifier would need its own
accuracy evaluation and prompt, and this phase's kickoff asked for a
"carefully scoped, auditable pipeline," not a second AI-assisted
component ahead of the answering model itself.

**Retrieval (§3), realized as two paths over `search_documents`, not
three over raw domain tables:**
- **Lexical**: reuses `app.search.service.search_documents` verbatim —
  the same ranking/typo-tolerance logic every browse/search page
  depends on already. No separate "structured retrieval" query layer
  was built; `search_documents` already carries `state_id`/`category`/
  `status`/date filters, so a future intent layer could add filtered
  queries without a new retrieval mechanism.
- **Semantic**: cosine similarity over a new `ai_knowledge_chunks`
  table, computed in **Python, not pgvector**. Verified by hand: this
  project's actual local/test PostgreSQL distribution ships no `vector`
  extension, and this development environment has no Docker (the usual
  way to get a pgvector-enabled Postgres) — see
  `tests/_full_pg_utils.py`'s own documented constraint. The kickoff's
  own wording ("store embeddings... in PostgreSQL/pgvector **if
  feasible within the existing setup**") explicitly anticipates this
  case. A bounded, capped Python-side candidate scan is adequate at
  this project's actual current scale (fixture-only content; no real
  government data before Phase 13) and is an honestly disclosed
  limitation, not a claim of production-scale performance
  ([DATABASE.md](DATABASE.md) §16 has the full writeup, including the
  swap path to a real `vector(N)` column later).
- Both paths implicitly enforce §3's `VERIFIED`/`NEEDS_REVIEW`-only
  rule for free: `ai_knowledge_chunks` has no FK to
  `search_documents`, but retrieval always joins the two tables on
  `(entity_type, entity_id, locale)`, so an entity that drops out of
  `search_documents` (unpublished, expired, soft-deleted) simply stops
  being retrievable — the same trust gate every domain's search
  indexing already relies on, reused rather than re-implemented.

**Context assembly (§4) uses a structured JSON response contract, not
inline citation markers in free text.** The model is instructed to
return exactly one JSON object
(`{"answer": ..., "citation_ids": [...], "grounded": ...}`), which
`app.ai.citations` parses and validates against the actual retrieved
evidence set — any `citation_ids` entry that isn't a genuine, in-range
integer id from the evidence given to that specific request is dropped
before anything reaches the user. A structured contract is what makes
server-side citation validation tractable at all; free-text citation
markers would require fragile text parsing to achieve the same
guarantee.

**LLM layer (§5), realized via direct `httpx` calls, not vendor SDKs.**
`app.ai.providers.LLMProvider`/`EmbeddingProvider` are `Protocol`s;
`AnthropicLLMProvider` (`providers_anthropic.py`) and
`OpenAIEmbeddingProvider` (`providers_openai.py`) are the two concrete
adapters, each a thin `httpx` wrapper rather than the `anthropic`/
`openai` Python SDKs — avoiding two additional dependency trees for one
REST endpoint each (CLAUDE.md rule 13). Both default to `"none"` — the
app builds, boots, and runs its full test suite with the LLM/embedding
layer entirely disabled, per this phase's explicit requirement. These
are genuinely independent, separately-configured provider credentials
(`AI_LLM_API_KEY`, `AI_EMBEDDING_API_KEY`) — Anthropic has no public
embeddings endpoint as of this writing, so a single "one vendor for
everything" assumption was never realistic here.

**Response contract (§6), realized as four `GroundingStatus` values,
not three plus a confidence score:**
`GROUNDED` / `UNGROUNDED` / `INSUFFICIENT_EVIDENCE` /
`PROVIDER_UNAVAILABLE`. The last two are new, deliberate splits from
§6's "ungrounded" bucket: `INSUFFICIENT_EVIDENCE` means retrieval found
nothing at all (the LLM is never even called — a direct cost-control
win); `PROVIDER_UNAVAILABLE` means no provider is configured or the
provider call itself failed, distinct because search/browse remains
available either way and the UI's messaging should say so. A
free-floating numeric "confidence" was not implemented — a fine-grained
partially-grounded score would need reliable claim-level entailment
checking this phase did not attempt to build reliably; the citation-
validity check (binary: did ≥1 real citation survive validation) is
what actually gates `GROUNDED` vs `UNGROUNDED`, with the model's own
self-reported `grounded` flag carried informationally only, never
overriding the server-side computation.

**Eligibility integration**, per this phase's explicit mandate:
`app.ai.eligibility_explainer.explain_eligibility` calls
`app.eligibility.service`'s real public functions
(`resolve_entity`/`get_evaluable_rule`/`run_evaluation`) unmodified — the
exact code path `/api/v1/eligibility/evaluate` uses — and only ever
*phrases* the `EligibilityOutcome` that comes back. The model is asked
to also self-report a `stated_outcome`; if that doesn't match the real
outcome exactly (or the response doesn't parse), the model's phrasing is
discarded entirely and a template built directly from the evaluation
trace is used instead — proven directly by
`tests/test_ai/test_eligibility_explainer.py::
test_llm_contradicting_the_real_outcome_is_discarded`, which uses a fake
provider that actively tries to state the wrong outcome.

**Safety & abuse (§7), realized:**
- Prompt injection: every piece of retrieved evidence is wrapped in an
  `<evidence id="N">` tag (`app.ai.prompting.build_evidence_block`), with
  the system prompt explicitly instructing the model to treat tag
  contents as data even if it looks like an instruction. This is
  structural (the wrapping happens unconditionally), not a content
  filter trying to detect injection attempts.
- Data isolation: no `Profile` data is read anywhere in this module —
  the general Q&A path takes only the submitted question, and the
  eligibility-explanation path takes only submitted answers, matching
  Phase 11's identical "no session exists to attach a profile to"
  finding.
- Rate limiting: realized as an **in-process, single-instance, per-IP
  sliding window** (`app.ai.rate_limit`) scoped to `/api/v1/ai/*`
  specifically — a deliberately minimal MVP, disclosed as such, since no
  rate-limiting infrastructure of any kind exists anywhere else in this
  codebase yet (verified by hand). `OBSERVABILITY.md`-level usage
  monitoring was not built (no such module/dashboard exists yet in this
  codebase).

**Evaluation (§8), realized as deterministic unit/integration tests, not
a live-model eval suite:** `tests/test_ai/` covers citation-fabrication
rejection, prompt-injection-wrapping structure, provider-unavailable
degradation, and the eligibility-non-interference property, all against
fake providers (no live credentials required or used in the test
suite, per this phase's explicit testing requirement). Real-model
groundedness/citation-accuracy quality (as opposed to the mechanical
guarantee that an *invalid* citation can never surface) is not measured
here — that requires real provider calls against real content, neither
of which this phase has.

This document now reflects the realized Phase 12 implementation; it is
extended, not rewritten, as retrieval/provider capabilities grow.
