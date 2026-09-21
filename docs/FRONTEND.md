# CivicLens — Frontend Architecture

This document defines the target Next.js frontend architecture and design
system **specification** — visual direction, structure, and conventions,
not implemented components. It is the reference for Phase 4 ("Frontend +
Design System" — [ROADMAP.md](ROADMAP.md)), refined against real content
needs starting Phase 6. **No frontend code exists yet.**

## 1. Scope & Relationship to Other Docs

- Technology choice and rendering rationale: [ADR-002](ADR/ADR-002-nextjs-frontend.md).
- API contract consumed by every page: [API.md](API.md), via the generated
  typed client in `packages/types`.
- Engines G (Life Event Navigator) and H (Personal Civic Dashboard) are
  frontend composition layers per [ARCHITECTURE.md](ARCHITECTURE.md) §5 —
  this document is where their realization is defined, since neither owns
  new backend data ([DATABASE.md](DATABASE.md) §1).
- SEO requirements that constrain rendering strategy: [SEO.md](SEO.md).
- Accessibility floor: WCAG 2.1 AA, per NFR-ACC1
  ([PRODUCT_REQUIREMENTS.md](PRODUCT_REQUIREMENTS.md) §2.5).

## 2. Page / Route Structure

Routes are locale-prefixed (§7) under Next.js App Router, one route group
per product surface, matching [PRODUCT.md](PRODUCT.md) §5's domains:

```
/[locale]/                          Home
/[locale]/search                    Search
/[locale]/jobs, /jobs/{slug}        Jobs
/[locale]/exams, /exams/{slug}      Exams
/[locale]/schemes/{slug}            Schemes
/[locale]/services/{slug}/{state}   Services
/[locale]/documents/{slug}          Documents & Certificates
/[locale]/scholarships/{slug}       Scholarships
/[locale]/representatives/{state}/{constituency}   Representatives
/[locale]/elections/{state}/{constituency}         Elections
/[locale]/calculators/{slug}        Calculators
/[locale]/eligibility/{slug}        Eligibility check
/[locale]/ai                        Civic AI
/[locale]/dashboard/tracking        Tracking (authenticated)
/[locale]/dashboard/profile         Profile (authenticated)
/[locale]/about, /contact, /privacy, /terms, /disclaimer   Static/legal
```

Exact slug/URL conventions (canonicalization, trailing structure) are
defined in [SEO.md](SEO.md) §1 — this section defines page inventory and
route grouping only, not the final URL grammar.

## 3. Rendering Strategy

Chosen per page type, not globally, per [ADR-002](ADR/ADR-002-nextjs-frontend.md):

| Page type | Strategy | Why |
|---|---|---|
| Home, About, legal pages | SSG | Static content, maximal cache, zero backend load |
| Job/exam/scheme/service/scholarship detail | ISR (revalidate on a interval + on-demand revalidation from ingestion publish) | SEO-critical, changes infrequently but must reflect approved `change_records` promptly ([DATA_GOVERNANCE.md](DATA_GOVERNANCE.md)) |
| Representative/election pages | ISR | Same rationale; low change frequency, high SEO value |
| Search results | SSR | Query-dependent, not cacheable per-URL at MVP corpus size ([SEARCH.md](SEARCH.md)) |
| Calculators, Eligibility check | SSR shell + client-side interactivity | Public and SEO-indexable (the check itself is client-side once loaded), but the wrapping page must be crawlable |
| Civic AI | Client-side (CSR) within an SSR shell | Conversational, stateful, not SEO-relevant content |
| Dashboard (tracking, profile) | CSR, authenticated | Personalized, never publicly cached or indexed |

On-demand ISR revalidation is triggered by the publish step of the
ingestion review pipeline ([DATA_SOURCES.md](DATA_SOURCES.md) §4,
Phase 13) — a change is never live in the CDN cache without having passed
human review first.

## 4. Component Architecture

- Three-tier component structure: **primitives** (button, input, badge,
  card — design-system tokens applied, no domain knowledge),
  **patterns** (source-attribution block, verification-status badge,
  eligibility-condition row, deadline timeline — domain-shaped but reused
  across multiple pages), and **page compositions** (a job detail page
  assembles patterns + primitives; owns layout, not visual rules).
- Domain-specific data shapes come from `packages/types`
  (generated from the OpenAPI schema, [API.md](API.md) §10) — no
  component hand-declares a type that duplicates a backend model.
- Server Components by default (App Router); a component opts into Client
  Component status only when it needs interactivity, browser APIs, or
  state — kept minimal to preserve SSR/SSG benefits.

## 5. State Management

- No global client-state library at MVP (no Redux/Zustand/etc. by
  default) — React Server Components + URL state (search filters, page
  number) + React `useState`/`useReducer` for local component state cover
  the identified needs, consistent with avoiding premature dependencies
  ([CLAUDE.md](../CLAUDE.md) rule 13).
- Server data fetching uses the generated typed client directly in Server
  Components/Route Handlers where possible; client-side data fetching
  (dashboard, Civic AI) uses a minimal fetch-and-cache pattern (e.g.,
  `swr`/`react-query`-class library) — the specific library is an
  implementation decision at Phase 4, not fixed here, and must be justified
  against what App Router already provides before adding it.
- Authenticated session state (JWT) lives in an httpOnly cookie set by the
  backend per [ADR-009](ADR/ADR-009-authentication-strategy.md) and
  [SECURITY.md](SECURITY.md) — never in `localStorage`.

## 6. Design System Specification

Visual direction — **modern, trustworthy, restrained**, appropriate for a
civic-trust product, not a consumer/marketing product:

- **Color**: deep navy as the primary brand/surface-accent color, white/
  near-white as the dominant surface color. Saffron and green used only as
  restrained accent colors (status highlights, small UI accents) —
  deliberately not a literal, flag-derived color scheme applied broadly,
  to keep the product visually neutral per the political-neutrality
  requirement ([DATA_GOVERNANCE.md](DATA_GOVERNANCE.md) §5). Semantic
  colors (verified/needs-review/expired/unverified status, per
  [DATA_GOVERNANCE.md](DATA_GOVERNANCE.md) §4) are a distinct token set
  from brand accent colors, so status meaning is never confused with
  decoration.
- **Surfaces**: rounded cards (moderate radius, not pill-shaped), subtle
  shadows for elevation (not heavy drop-shadows), generous whitespace.
  Avoid excessive glassmorphism/blur effects — clarity and legibility over
  visual trend-chasing, since the audience includes low-bandwidth mobile
  users and older devices.
- **Typography**: a modern, highly legible sans-serif for English; a
  typeface with genuine Telugu script support and comparable weight/style
  range for Telugu content, so neither locale looks like an afterthought
  (see §7). Type scale is defined as design tokens, not per-component
  magic numbers.
- **Tokens**: color, spacing, radius, shadow, and type-scale values are
  defined once as design tokens (implementation detail decided at
  Phase 4 — CSS variables or a Tailwind theme config) and consumed by
  every primitive component — no component hardcodes a raw color/spacing
  value.
- **Mobile-first**: layouts are designed and tested at mobile viewport
  widths first, matching the primary access pattern for Indian civic
  information consumers, then progressively enhanced for larger screens.
- **Accessibility**: WCAG 2.1 AA is the floor (NFR-ACC1) — sufficient
  color contrast (including for status badges), visible focus states,
  semantic HTML landmarks, and full keyboard operability for search, view,
  and eligibility-check flows (NFR-ACC2). Accessibility is validated with
  automated checks (e.g., axe) in component tests plus manual keyboard/
  screen-reader passes for core flows — not automated checks alone.

## 7. Internationalization (English / Telugu)

- Locale-aware routing: `/en/...`, `/te/...`, matching
  [ARCHITECTURE.md](ARCHITECTURE.md) §10. A locale-detection redirect at
  `/` sends first-time visitors to a default locale; the choice is
  sticky (cookie), never re-guessed on every visit.
- UI chrome (navigation, buttons, labels) is translated via locale
  catalogs (e.g., Next.js `next-intl`/App Router i18n conventions —
  specific library chosen at Phase 4). Domain content (job titles,
  scheme descriptions) is translated at the data layer
  ([DATABASE.md](DATABASE.md) §0.4 translatable fields), not machine-
  translated at render time — content translation quality is a data/
  editorial concern, not a frontend rendering trick.
- If a translated content field is unavailable for a given locale, the UI
  falls back to the source-language content with a visible "not yet
  translated" indicator — it never silently machine-translates or hides
  the item, per NFR-I18N1 (translations are first-class, not an
  afterthought).
- Number, date, and currency formatting use locale-aware formatting
  (`Intl` APIs), not hardcoded formats.

## 8. Life Event Navigator (Engine G)

A **frontend composition layer**, not a new data domain
([ARCHITECTURE.md](ARCHITECTURE.md) §5, [DATABASE.md](DATABASE.md) §1). It
is realized as:

- A curated set of "life event" entry points (e.g., "I finished my
  degree," "I need a certificate") defined as frontend configuration/
  content, mapping a life event to a query composition — a predefined
  combination of domain filters (category, qualification, state) and
  cross-domain result grouping (jobs + exams + scholarships that match).
- It calls the same public read endpoints as direct browsing
  ([API.md](API.md) §3) with pre-set filters; it introduces no new backend
  route or table. Expanding the set of life events is a content/config
  change, not a schema or API change — consistent with the state-agnostic,
  data-driven design principle ([ARCHITECTURE.md](ARCHITECTURE.md) §3).

## 9. Personal Civic Dashboard (Engine H)

Also a composition layer, authenticated, aggregating existing read
endpoints for the current user:

- Saved items (`saved_items`), tracked items (`tracking_items`), upcoming
  deadlines (from tracked entities' `deadlines`), and — only where the
  user explicitly provided profile attributes — a document checklist
  (from [ELIGIBILITY_ENGINE.md](ELIGIBILITY_ENGINE.md) §documents linkage).
- The dashboard never infers or displays a personalization based on data
  the user did not explicitly provide (FR-P2,
  [PRODUCT_REQUIREMENTS.md](PRODUCT_REQUIREMENTS.md) §1.9) — it is a
  read-aggregation view, not a recommendation engine.

## 10. Explicitly Not Built Yet

- Any actual page, component, or design token implementation.
- Choice of specific client-state/data-fetching libraries beyond the
  constraints in §5 (decided at Phase 4 against real page needs).
- A component library published as a standalone package — components live
  in `apps/web` until (if ever) a documented reuse need justifies
  extraction.

This document defines the target frontend and design-system specification
for Phase 4; it is finalized against a real component inventory once
Phase 4 implementation begins, and validated against real content pages
starting Phase 6.
