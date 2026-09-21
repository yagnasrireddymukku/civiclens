# CivicLens — Product Vision

## 1. What CivicLens Is

CivicLens is India's personal public-information intelligence platform. It helps
citizens move from raw government information to a concrete next action:

**Search → Understand → Check → Prepare → Act → Track**

CivicLens is not a news aggregator, not a government-scheme blog, and not a
generic search engine. It is a structured, verified, source-grounded system
that answers one question for a real person:

> "What does this public information mean for me, and what can I do next?"

## 2. Who It Is For

Initial launch geography: **Andhra Pradesh + Telangana**. The product
architecture is state-agnostic (see [ARCHITECTURE.md](ARCHITECTURE.md) §3);
AP/TS are configuration and data, not hardcoded assumptions.

Primary users at launch:
- Job seekers tracking government recruitment (jobs, exams, results)
- Students and families navigating scholarships and education services
- Citizens who need a government service or certificate and don't know the
  process, documents, or office
- Citizens who want factual, dated information about representatives and
  elections in their constituency

## 3. Core Differentiator

CivicLens does not merely display information. It transforms it:

```
INFORMATION → UNDERSTANDING → ELIGIBILITY → PREPARATION → ACTION → TRACKING
```

Worked example — a user searches "I'm 23, completed B.Tech CSE, looking for
government opportunities in Andhra Pradesh":

1. **Understand intent** — degree, age, state, opportunity-seeking
2. **Identify categories** — jobs, exams matching degree/age
3. **Check eligibility** — deterministic rule evaluation against structured
   eligibility rules (never an LLM guess — see
   [ELIGIBILITY_ENGINE.md](ELIGIBILITY_ENGINE.md))
4. **Explain the match** — why this opportunity applies, in plain language
5. **Show requirements** — documents, dates, official source
6. **Enable tracking** — the user can follow it and gets notified on change

This end-to-end chain, backed by verified structured data, is what
distinguishes CivicLens from any government portal or news site. This chain
is the product's north star; it is **not** built in the initial release (see
[ROADMAP.md](ROADMAP.md)), but every architectural decision must keep it
reachable.

## 4. Product Engines

CivicLens is organized around eight engines. Each is described architecturally
in [ARCHITECTURE.md](ARCHITECTURE.md) §5 and in its own document where noted.

| Engine | Purpose | Detail |
|---|---|---|
| A. Civic Search Engine | Keyword + natural-language discovery | [SEARCH.md](SEARCH.md) |
| B. Civic AI | Source-grounded explanation and Q&A | [AI_ARCHITECTURE.md](AI_ARCHITECTURE.md) |
| C. Eligibility Engine | Deterministic rule evaluation | [ELIGIBILITY_ENGINE.md](ELIGIBILITY_ENGINE.md) |
| D. Civic Timeline | Time-sensitive stage tracking (notification → result) | [DATABASE.md](DATABASE.md) §deadlines |
| E. Tracking & Alerts | User subscriptions to entities and deadlines | [DATABASE.md](DATABASE.md) §tracking |
| F. Document Intelligence | Required-document checklists and explanations | [ELIGIBILITY_ENGINE.md](ELIGIBILITY_ENGINE.md) §documents |
| G. Life Event Navigator | Organizes information around real situations, not bureaucratic categories | [FRONTEND.md](FRONTEND.md) |
| H. Personal Civic Dashboard | Saved items, tracked opportunities, personalized view | [FRONTEND.md](FRONTEND.md) |

The AI layer (Engine B) is explicitly **not** the source of truth for any of
the other engines. It explains and synthesizes what the structured system
already knows. See [DATA_GOVERNANCE.md](DATA_GOVERNANCE.md).

## 5. Initial Information Domains

1. Government Jobs
2. Government Exams
3. Government Services
4. Government Schemes
5. Scholarships
6. Public Representatives
7. Elections / Public Records
8. Documents & Certificates
9. Eligibility
10. Calculators
11. Civic AI
12. Tracking & Alerts

The first release favors depth and correctness in a narrow scope
(AP + Telangana, a subset of these domains) over shallow national coverage.
See [ROADMAP.md](ROADMAP.md) for sequencing.

## 6. Non-Goals (v1 and beyond, unless explicitly revisited)

- Not a political persuasion, ranking, or recommendation platform
  ([DATA_GOVERNANCE.md](DATA_GOVERNANCE.md) §5)
- Not a general-purpose chatbot — Civic AI only answers from grounded sources
- Not an ads-first product — monetization never compromises factual accuracy
  ([MONETIZATION.md](MONETIZATION.md))
- Not a scraping-everything platform — ingestion respects law, ToS, and
  licensing ([DATA_SOURCES.md](DATA_SOURCES.md))
- Not a single-state permanent product — AP/TS is a starting scope, not a
  ceiling

## 7. Success Definition for v1

A user in AP or Telangana can:
1. Search for a job, exam, scheme, or service in plain English or Telugu
2. See verified information with a source and a "last verified" date
3. Understand, in plain language, whether it likely applies to them
4. See what documents/steps are needed
5. Track it and be notified if it changes

Trust is the product. A wrong date or a fabricated scheme is a
worse outcome than an empty result page.
