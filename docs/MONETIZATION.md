# CivicLens — Monetization Architecture

## 0. Monetization Is Not the Design Center

Read this section before any other. CivicLens exists to give citizens
trustworthy, actionable civic information ([PRODUCT.md](PRODUCT.md) §1).
Monetization is a **later, secondary layer** on top of that purpose, not a
constraint that shapes it. Concretely:

- **User trust and utility come before revenue**, always. Where a
  monetization mechanism would create even a plausible perception of
  pay-to-play access to public benefits, biased information, or reduced
  factual accuracy, it is rejected outright — no revenue target justifies
  it. See [PRODUCT.md](PRODUCT.md) §6: "Not an ads-first product."
- **Advertising and sponsorship must never be visually confusable with
  verified civic data or Civic AI answers.** An ad must always be
  unambiguously, visibly distinct (labeling, placement, styling) from a
  job/scheme/eligibility result or an AI-generated explanation. This is a
  hard requirement, not a design preference — see §1.
- **No monetization feature is built in the initial release or the phases
  leading up to it.** Per [ROADMAP.md](ROADMAP.md), monetization is
  **Phase 18 (Post-launch Expansion)** territory: evaluated only after a
  successful launch with real users, and only pulled forward earlier with
  explicit, documented approval for a specific stream — never by default.
  Nothing in this document authorizes building any of the below now.

This document exists so that *when* monetization is eventually built, it
is built consistently with the architecture and governance already in
place — not as an afterthought bolted onto a system that wasn't designed
to accommodate it safely.

## 1. Revenue Stream 1 — Display Advertising

Contextual/programmatic display ads on public pages (e.g., job listings,
scheme pages).

**Architectural implication**: ad placements must be structurally
separated from factual content in both markup and layout — never inline
within an eligibility result, a source citation block, or an AI answer.
The frontend's component structure ([FRONTEND.md](FRONTEND.md)) should
treat "ad slot" as its own component type that cannot be composed inside a
verified-data or AI-answer component, making the confusion this section
warns against structurally harder to introduce by accident. Ads must never
appear adjacent to an eligibility verdict in a way a user could read as
"pay to see if you qualify."

## 2. Revenue Stream 2 — Relevant Affiliate Partnerships

Clearly disclosed affiliate links for genuinely relevant resources — e.g.,
exam-prep books/courses on a government-exam page.

**Architectural implication**: affiliate content must be a distinctly
labeled, separate data type from official source-linked content
([DATA_GOVERNANCE.md](DATA_GOVERNANCE.md) §2, "four kinds of content, never
conflated") — an affiliate link is never stored or rendered as if it were
a `source`/citation. **Hard boundary**: affiliate partnerships are never
placed on or adjacent to scheme, scholarship, or eligibility pages in a
way that could look like payment for access to a public benefit — exam-
prep-adjacent placements only, disclosed as sponsored/affiliate at the
point of display.

## 3. Revenue Stream 3 — Premium Alerts

Paid tier for faster and/or richer tracking notifications (e.g., instant
push vs. daily digest, richer change detail).

**Architectural implication**: the underlying `tracking`/`notifications`
data model ([DATABASE.md](DATABASE.md) §tracking) must support a delivery-
tier attribute per subscription without changing what data free users can
see — this is a delivery-speed/richness gate, never a gate on whether a
factual change is visible at all. Free users must still receive every
notification they're entitled to; paying only changes latency/format.

## 4. Revenue Stream 4 — Premium Personalization

Paid tier for deeper personalization (e.g., more saved items, finer-
grained life-event navigation, expanded dashboard views).

**Architectural implication**: personalization features live in the
`users`/`profiles` and composition layers already described for Engine H
(Personal Civic Dashboard, [ARCHITECTURE.md](ARCHITECTURE.md) §5) — a paid
tier is a limit/entitlement check on top of existing composition, not a
separate data model. The underlying facts and search/eligibility results
shown are identical regardless of tier; only breadth/depth of
personalization differs.

## 5. Revenue Stream 5 — Advanced Civic AI

Paid tier for the AI engine: higher usage/rate limits, deeper or longer
explanations, possibly access to more advanced retrieval or model
configurations.

**Architectural implication**: tiering hooks into the `ai` module's
existing rate-limiting point ([AI_ARCHITECTURE.md](AI_ARCHITECTURE.md) §7)
as a per-tier limit value, not a separate AI pipeline. **Hard boundary**:
a paid tier may change usage limits, response depth, or latency — it must
never change groundedness standards, citation requirements, or the
provider-abstraction safety constraints in
[AI_ARCHITECTURE.md](AI_ARCHITECTURE.md) §5. A free user and a paying user
receive equally accurate, equally cited answers; paying buys more of the
same trustworthy thing, not a "better-verified" tier implying the free
tier is less trustworthy.

## 6. Revenue Stream 6 — Career/Education Tools

Value-added tools adjacent to the core product (e.g., structured exam-
prep planners, application trackers with guided steps) — potentially
freemium.

**Architectural implication**: these are additive composition features
over existing domain data (jobs/exams/scholarships) and the tracking
engine, not a new source-of-truth. They should not introduce a second,
parallel notion of "eligibility" or "deadline" outside the existing
Eligibility Engine and Civic Timeline ([ARCHITECTURE.md](ARCHITECTURE.md)
§5) — a career tool consumes those engines' outputs, it does not
reimplement them.

## 7. Revenue Stream 7 — API Access (B2B)

A rate-limited, paid tier of API access to CivicLens's structured, verified
civic data, for external developers/organizations.

**Architectural implication**: a paid API tier is built on the **same**
underlying API and data model documented in [API.md](API.md) — not a
forked or lower-quality data path. Every record served through a paid API
tier carries the same source/provenance/verification metadata
([DATA_GOVERNANCE.md](DATA_GOVERNANCE.md) §3) as the public-facing API and
UI; CivicLens does not sell a "cleaner" or "faster" version of facts that
differs from what free users see. Differentiation is: rate limits, request
volume, possibly bulk/batch endpoints, and an API key/billing layer on top
of the existing JWT auth model (ADR-009) — not a second data pipeline.

## 8. Revenue Stream 8 — B2B Data Services

Broader data licensing/services to institutions (e.g., aggregated,
anonymized usage insights, or structured data feeds beyond the API-access
tier).

**Architectural implication**: any B2B data product must respect the same
privacy constraints as the rest of the system ([PRIVACY.md](PRIVACY.md)) —
individual user data is never sold or exposed in aggregate form that could
be de-anonymized. Civic factual data (jobs, schemes, representative
records) already public in the product can be licensed for structured
access; personal user behavior data is a categorically different, far more
constrained case and requires its own explicit privacy review before any
such offering is designed in detail — this document does not pre-approve
that design, only flags the distinction.

## 9. Cross-Cutting Rules for Every Stream

1. **No stream may compromise factual presentation.** No ranking,
   placement, or emphasis of civic facts (jobs, schemes, representatives,
   eligibility results) may be influenced by payment. This extends the
   political-neutrality doctrine ([DATA_GOVERNANCE.md](DATA_GOVERNANCE.md)
   §5) to commercial neutrality: paying for visibility of a *product
   feature* is acceptable (e.g., premium alerts); paying for
   *prominence or alteration of a civic fact* is never acceptable.
2. **Visual distinctness is mandatory.** Any monetized element (ad,
   affiliate link, sponsored placement) must be immediately
   distinguishable from verified data and from Civic AI output — by
   labeling, container styling, and placement — enforced at the design-
   system level ([FRONTEND.md](FRONTEND.md)), not left to per-page
   discretion.
3. **Provenance parity for paid data access.** Any stream that exposes
   CivicLens's structured data externally (Streams 7–8) must carry the
   same source/verification metadata as the public product. Selling
   "verified" data without its verification trail would itself be a
   trust violation.
4. **Free tier remains genuinely useful.** No core product engine from
   [PRODUCT.md](PRODUCT.md) §4 (Search, Civic AI at a reasonable baseline,
   Eligibility, Timeline, Tracking, Document Intelligence, Life Event
   Navigator, Personal Dashboard) is reduced to a non-functional teaser to
   force upgrades — paid tiers add depth/speed/scale, they do not
   withhold baseline utility.

## 10. Explicitly Not Built Yet

- No payment processing, billing, subscription, or entitlement system
  exists.
- No ad-serving integration, affiliate-network integration, or API-key/
  billing infrastructure exists.
- No pricing, tier definitions, or specific partner/vendor relationships
  are decided — this document is architectural guardrails, not a pricing
  plan.
- No stream listed above is scheduled before
  [ROADMAP.md](ROADMAP.md) Phase 18, except by explicit, separately
  documented approval to pull a specific stream forward.

## 11. Related Documents

- [PRODUCT.md](PRODUCT.md) — product vision and non-goals this document
  must remain subordinate to
- [ARCHITECTURE.md](ARCHITECTURE.md), [AI_ARCHITECTURE.md](AI_ARCHITECTURE.md) —
  engines that monetization tiers hook into without altering
- [API.md](API.md), [DATA_GOVERNANCE.md](DATA_GOVERNANCE.md) — provenance
  and API-contract requirements a paid API tier must preserve
- [PRIVACY.md](PRIVACY.md) — constraints on any B2B data service involving
  user data
- [ROADMAP.md](ROADMAP.md) Phase 18 — when this document's target state
  is actually evaluated for implementation
