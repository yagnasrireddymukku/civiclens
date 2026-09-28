# CivicLens — Frontend Architecture

This document defines the Next.js frontend architecture and design
system. **Phase 4 status**: the design system (tokens, primitives,
CivicLens-specific components), application shell, and English/Telugu
i18n foundation are implemented (`apps/web/components/`,
`apps/web/app/globals.css`, `apps/web/i18n/`) — see §4, §6, §7, §11 for
what's real today. No domain content pages exist yet; those land
incrementally starting Phase 6 against this foundation.

## 1. Scope & Relationship to Other Docs

- Technology choice and rendering rationale: [ADR-002](ADR/ADR-002-nextjs-frontend.md).
- API contract consumed by every page: [API.md](API.md), via the generated
  typed client in `packages/types`.
- Engines G (Life Event Navigator) and H (Personal Civic Dashboard) are
  frontend composition layers per [ARCHITECTURE.md](ARCHITECTURE.md) §5 —
  this document is where their realization is defined, since neither owns
  new backend data ([DATABASE.md](DATABASE.md) §1).
- SEO requirements that constrain rendering strategy: [SEO.md](SEO.md).
- Accessibility floor: WCAG 2.2 AA, per NFR-ACC1
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
/[locale]/login, /register          Sign in / create account
/[locale]/admin                     Admin dashboard (editor/admin)
/[locale]/admin/change-records      Change-record review queue (editor/admin)
/[locale]/admin/verification        Verification queue (editor/admin)
/[locale]/admin/sources             Source browser, read-only (editor/admin)
/[locale]/about, /contact, /privacy, /terms, /disclaimer   Static/legal
```

`/login` and `/register` were not in this document's original route
inventory above — added when Tracking + Notifications (rescheduled from
Phase 12) realized real authentication (§4/§11 below), following the
same `app/[locale]/<name>/page.tsx` convention as every other route.
`/admin/*` is likewise new — ROADMAP.md's original Phase 13 sketch
named the folder `apps/web/app/admin/` without a `[locale]` segment;
placed under `[locale]` here instead, for consistency with every other
route and to satisfy this phase's explicit English/Telugu
localization requirement, which an unlocalized folder couldn't.

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
| Admin console (dashboard, change-records, verification, sources) | CSR, `editor`/`admin`-only | Privileged, never publicly cached, indexed, or crawlable (`robots: {index: false}` on every `/admin/*` page) — same rationale as Dashboard, plus role, not just identity |

On-demand ISR revalidation is triggered by the publish step of the
ingestion review pipeline ([DATA_SOURCES.md](DATA_SOURCES.md) §4,
Phase 13) — a change is never live in the CDN cache without having passed
human review first. **Not yet real**: the admin console realized this
phase (§12 below) reviews `ChangeRecord`s and submits verification
decisions, but no ingestion pipeline or publish step exists to trigger
an on-demand revalidation from — every domain detail page still relies
on its own ISR interval, unchanged by this phase.

## 4. Component Architecture

Realized as five folders under `apps/web/components/`, each with an
`index.ts` barrel:

| Folder | Contains | Examples |
|---|---|---|
| `primitives/` | Generic atoms, no domain knowledge | Button, Input, Textarea, Select, Checkbox, RadioGroup, Switch, Card, Badge, Divider, Skeleton, Spinner |
| `feedback/` | Overlays and status surfaces | Alert, Tooltip, Dialog, Toast (+ `ToastProvider`) |
| `navigation/` | Wayfinding | Tabs, Breadcrumb, Pagination, Dropdown |
| `layout/` | App shell | AppShell, TopNav, Footer, Container, LanguageSwitcher |
| `civic/` | CivicLens-specific, domain-shaped but not domain-data-owning | SourceBadge, VerificationStatus, LastVerified, OfficialSourceCard, EligibilityStatus, DeadlineBadge, SearchResultCard, InformationCard, SearchBar |
| `auth/` | Session state (Tracking + Notifications, rescheduled from Phase 12) | `AuthProvider`/`useAuth` — a client Context mirroring the current user, mounted once in `app/[locale]/layout.tsx` alongside `ToastProvider` |
| `tracking/` | Tracking + Notifications, rescheduled from Phase 12 | `TrackButton` — the real track/untrack control embedded on job/scheme/service/document detail pages |

Conventions:
- Each component is one `.tsx` + one co-located `.module.css` file (no
  per-component subfolder) — kept flat since a folder-per-component adds
  structure without benefit at this scale.
- Every civic component's props are the data it needs, supplied by the
  caller — none of them fetch, and none contain placeholder real-looking
  government content (docs/DATA_GOVERNANCE.md §7). Fixture text used in
  the design-system showcase (§9) is unambiguously fictional.
- `VerificationStatus`, `EligibilityStatus`, and `DeadlineBadge` mirror
  enum values from `apps/api` (`app/sources/enums.py`,
  [ELIGIBILITY_ENGINE.md](ELIGIBILITY_ENGINE.md) §3) exactly — the
  frontend doesn't invent its own status vocabulary.
- A hand-authored icon set (`components/icons.tsx`, ~8 icons) is used
  instead of an icon package dependency (this phase's "avoid giant icon
  packages" rule).
- Domain-specific data shapes will come from `packages/types`
  (generated from the OpenAPI schema, [API.md](API.md) §10) once real
  domain endpoints exist (Phase 6+) — no component hand-declares a type
  that duplicates a backend model.
- Server Components by default (App Router); a component opts into Client
  Component status only when it needs interactivity, browser APIs, or
  state (`TopNav` for the mobile menu toggle, `LanguageSwitcher`,
  `Dialog`, `Toast`, `Tabs`, `SearchBar`) — kept minimal to preserve
  SSR/SSG benefits.

Accessible-by-construction choices worth naming explicitly, since they
avoid a UI-library dependency (this phase's rule) by leaning on native
HTML behavior:
- **Select** wraps the native `<select>` (full keyboard/mobile-picker
  support for free).
- **Dialog** wraps the native `<dialog>` element + `showModal()` (native
  focus trap, `Escape`-to-close, top-layer rendering).
- **Dropdown** is built on `<details>/<summary>`.
- **Tabs** hand-implements the WAI-ARIA tabs pattern (roving tabindex,
  arrow-key navigation) since no native element covers it.
- **Tooltip** is CSS-only (`:hover`/`:focus-within`), no positioning
  library.
- **Switch** is a native checkbox with `role="switch"` (ARIA 1.2).

## 5. State Management

- No global client-state library (no Redux/Zustand/etc.) — React Server
  Components + URL state (search filters, page number) + React
  `useState`/`useReducer` for local component state cover the identified
  needs, consistent with avoiding premature dependencies
  ([CLAUDE.md](../CLAUDE.md) rule 13). The one small exception is
  `ToastProvider` (`components/feedback/Toast.tsx`), a plain React
  Context holding an in-memory toast queue — deliberately not a general
  state-management pattern, just the minimum needed for a cross-tree
  transient-notification API.
- Server data fetching uses the generated typed client directly in Server
  Components/Route Handlers where possible; client-side data fetching
  (dashboard, Civic AI) uses a minimal fetch-and-cache pattern (e.g.,
  `swr`/`react-query`-class library) — the specific library is an
  implementation decision at Phase 4, not fixed here, and must be justified
  against what App Router already provides before adding it.
- Authenticated session state (JWT) lives in an httpOnly cookie set by the
  backend per [ADR-009](ADR/ADR-009-authentication-strategy.md) and
  [SECURITY.md](SECURITY.md) — never in `localStorage`.
- **Realized (Tracking + Notifications, rescheduled from Phase 12):**
  no `swr`/`react-query`-class library was added — the dashboard,
  `TrackButton`, and the login/register forms all use the same plain
  `fetch`-in-a-`useState`-driven-handler pattern Eligibility/Civic AI
  already established (§12), via new `lib/auth.ts`/`lib/tracking.ts`/
  `lib/notifications.ts` wrappers following `lib/jobs.ts`'s tagged-
  union-result convention exactly. `AuthProvider` (`components/auth/`)
  is the one small exception worth naming here — a plain React Context
  holding the current user + CSRF token, loaded once on mount via
  `GET /api/v1/auth/me` (with a single silent `POST /api/v1/auth/
  refresh` retry if the access-token cookie has simply expired) —
  deliberately minimal, the same "just enough Context, not a general
  state-management pattern" precedent `ToastProvider` already set
  above, not a second one invented for a different reason.

## 6. Design System Specification

Visual direction — **modern, trustworthy, restrained**, appropriate for a
civic-trust product, not a consumer/marketing product. All tokens live in
`apps/web/app/globals.css` as CSS custom properties on `:root`.

- **Styling approach**: plain CSS Modules + CSS custom properties — no
  Tailwind, no component-library dependency (this phase's "avoid
  unnecessary UI libraries" rule; also keeps the shipped CSS/JS small,
  per this phase's performance rule). Every component reads tokens via
  `var(--token-name)`; none hardcodes a raw color/spacing/radius/shadow
  value.
- **Color**: a deep-navy primary (`--color-primary`) with white/near-white
  surfaces (`--color-background`, `--color-surface`). A single restrained,
  desaturated warm `--color-accent` exists for sparing use (not applied
  broadly) — deliberately not a literal flag-derived scheme, keeping the
  product visually neutral per the political-neutrality requirement
  ([DATA_GOVERNANCE.md](DATA_GOVERNANCE.md) §5). Semantic tokens
  (`--color-success/warning/error/info`, each with a paired `-surface`
  tint) are a distinct set from brand tokens, so status meaning is never
  confused with decoration — and, per NFR-ACC2/§10 below, status is never
  conveyed by color alone: every status component (`VerificationStatus`,
  `EligibilityStatus`, `DeadlineBadge`) pairs its color with a distinct
  icon and text label.
- **Surfaces**: rounded cards (`--radius-lg`, moderate, not pill-shaped),
  subtle shadows for elevation (`--shadow-sm/md/lg`, low-opacity),
  generous whitespace via the spacing scale. No glassmorphism/blur
  effects.
- **Typography**: a system-font stack (`-apple-system, "Segoe UI", "Noto
  Sans Telugu", "Nirmala UI", Roboto, ...`) rather than a downloaded
  webfont — a deliberate choice that is both lighter (no extra network
  request) and solves Telugu rendering for free, since the OS's own UI
  font already covers Telugu glyphs on the platforms CivicLens targets.
  The full scale (`--text-display/h1/h2/h3/h4/body/body-small/caption/
  label/button`) is defined as shorthand `font` custom properties.
- **Spacing**: a 4px-based scale, `--space-1` (4px) through `--space-20`
  (80px).
- **Radii**: `--radius-sm/md/lg/xl/pill`.
- **Elevation**: `--shadow-sm/md/lg`, used only for cards (`elevated`
  variant), dropdowns, dialogs, and toasts — not applied decoratively.
- **Motion**: `--duration-fast/base/slow` + `--easing-standard`, used for
  hover/focus/expand transitions. A single global
  `prefers-reduced-motion: reduce` media query collapses all animation/
  transition durations to near-zero — applied once, globally, rather than
  requiring every component to remember a per-component guard.
- **Mobile-first**: unprefixed styles are the mobile layout; a component
  adds a `min-width` media query (documented breakpoints: 640/768/1024/
  1280px) only when content genuinely needs to reflow — see `TopNav`'s
  hamburger-to-inline-nav switch at 1024px as the concrete example.
- **Dark mode**: **not implemented** as a user-facing feature in this
  phase — no requirement in
  [PRODUCT_REQUIREMENTS.md](PRODUCT_REQUIREMENTS.md) names it, and adding
  one without a real need would be exactly the kind of unjustified scope
  this phase's own instructions warn against. Tokens are nonetheless
  defined as CSS custom properties on `:root` specifically so a future,
  complete dark theme could be added as a `:root[data-theme="dark"]`
  override block without a component-by-component redesign — a
  token-architecture choice, not a partial implementation. Revisit only
  with a stated product requirement.
- **Accessibility**: WCAG 2.2 AA is the floor — sufficient color contrast,
  a visible high-contrast focus ring on every interactive element
  (`:focus-visible` globally, never suppressed), semantic HTML landmarks,
  a skip-to-content link (`AppShell`), and full keyboard operability
  (verified for `Tabs` and `Dialog` by automated tests, see
  [TESTING.md](TESTING.md)). Status is never color-only (above). A
  development-only showcase page (§9) exists to visually spot-check all
  of this together.

## 7. Internationalization (English / Telugu) — implemented, Phase 4

- **Library**: `next-intl`, chosen over hand-rolling routing/catalogs — a
  single, purpose-built, actively-maintained dependency for exactly this
  need (justified per [CLAUDE.md](../CLAUDE.md) rule 13).
- **Routing**: `apps/web/i18n/routing.ts` defines the locale list
  (`en`, `te`) and `localePrefix: "always"` — every URL is
  locale-prefixed (`/en/...`, `/te/...`), matching
  [ARCHITECTURE.md](ARCHITECTURE.md) §10. `apps/web/proxy.ts` (Next.js's
  middleware/proxy convention) runs `next-intl`'s middleware, which
  redirects `/` to the negotiated locale and remembers the choice in a
  cookie (sticky — never re-guessed on a later visit to `/`). Adding a
  future locale (Hindi, Tamil, Kannada, Malayalam, Marathi, Bengali) is a
  one-line change to the locale list plus a new `messages/<code>.json`
  catalog — no component code changes.
- **App structure**: `app/layout.tsx` is a bare passthrough (no `<html>`/
  `<body>` — the locale isn't known yet at that level); `app/[locale]/
  layout.tsx` renders the actual document shell, validates the locale
  param (`notFound()` on an unrecognized one), and wraps children in
  `NextIntlClientProvider` + `AppShell`. This is `next-intl`'s documented
  App Router pattern, not a CivicLens invention.
- **Catalogs**: `apps/web/messages/en.json` and `te.json`, namespaced by
  UI area (`Shell`, `Nav`, `Footer`, `Home`, `NotFound`, `ErrorBoundary`,
  `Loading`, `DesignSystem`, `LanguageSwitcher`). Telugu strings are
  good-faith translations for this phase's shell/foundation surface —
  professional editorial review is a content task for a later phase
  (docs/FRONTEND.md's own principle below: translation quality is a
  data/editorial concern, not a frontend rendering trick), not something
  this phase certifies.
- **Switching**: `components/layout/LanguageSwitcher.tsx`, a native
  `<select>` using `next-intl`'s `useRouter`/`usePathname` to change
  locale while staying on the current page.
- Domain content (job titles, scheme descriptions — none exists yet) will
  be translated at the data layer ([DATABASE.md](DATABASE.md) §0.4
  translatable fields), not machine-translated at render time, once
  domain phases land.
- If a translated content field is unavailable for a given locale, the UI
  must fall back to the source-language content with a visible "not yet
  translated" indicator — it must never silently machine-translate or
  hide the item, per NFR-I18N1 (translations are first-class, not an
  afterthought). No content exists yet to exercise this; the rule is
  recorded here for the phase that first needs it.
- Number/date formatting uses locale-aware `Intl` APIs, not hardcoded
  formats — see `components/civic/LastVerified.tsx`
  (`Intl.DateTimeFormat`).

## 8. Application Shell — implemented, Phase 4

`components/layout/AppShell.tsx` wraps every page: a skip-to-content
link, `TopNav`, the page content in a `<main>` landmark, and `Footer`.

- **TopNav** (`components/layout/TopNav.tsx`): brand/logo, primary
  navigation, language control, and a user area. **Realized (Tracking +
  Notifications, rescheduled from Phase 12):** the placeholder described
  below is gone — a real `useAuth()`-driven "Sign in" link (to `/login`)
  when signed out, or a "Dashboard" link + working "Sign out" button
  when signed in, matching the same "no functional-looking control that
  does nothing" principle the placeholder itself was built to satisfy.
- **Primary navigation's "coming soon" pattern**: every future section
  named in [PRODUCT.md](PRODUCT.md) §5 (Jobs, Schemes, Services,
  Representatives, Exams, Documents, Calculators, AI Assistant) has no
  route yet. Per this phase's explicit instruction, these render as
  non-interactive, clearly-labeled items with a "Coming soon" badge and a
  tooltip — never as an `<a href>` to a route that 404s. The same
  principle applies to the footer's legal links (About/Contact/Privacy/
  Terms/Disclaimer): labeled text, not dead links, until those pages
  exist (Phase 6+).
- **Responsive**: a hamburger toggle below 1024px (`aria-expanded`/
  `aria-controls` wired to the nav panel); an inline horizontal nav at
  1024px and above.
- **Footer** (`components/layout/Footer.tsx`): tagline + the same
  labeled (not yet linked) legal items.

## 9. Design System Showcase — implemented, Phase 4

`app/[locale]/dev/design-system/` — an internal, development-only page
demonstrating every token category and component with fictional
placeholder content (this phase's §22/§27; fixtures follow
[DATA_GOVERNANCE.md](DATA_GOVERNANCE.md) §7 naming conventions, e.g.
"Test Board — Not Real"). It is **not a public CivicLens feature**,
enforced two ways:
1. `apps/web/proxy.ts` returns HTTP 404 for any `/{locale}/dev/*` path
   when `NODE_ENV === "production"`, before any rendering happens.
2. The page component itself also calls Next.js's `notFound()` under the
   same condition, as defense in depth for any request path that might
   bypass the proxy.

It also sets `robots: { index: false, follow: false }` regardless of
environment, so it can never be indexed even if reached.

## 10. Life Event Navigator (Engine G)

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

## 11. Personal Civic Dashboard (Engine H)

Also a composition layer, authenticated, aggregating existing read
endpoints for the current user. **Realized as `/dashboard/tracking`
(Tracking + Notifications, rescheduled from Phase 12)** — narrower
than this section's original sketch, and the scope difference is worth
naming rather than silently reinterpreting the sketch as fulfilled:

- Built: tracked items (`tracked_items`, [API.md](API.md) §19) with
  pause/resume/remove controls; upcoming deadlines, derived from the
  same tracked-items response rather than a separate fetch (real
  structured `deadline`/`deadline_expired` fields only — never
  inferred, [DATABASE.md](DATABASE.md) §18); the notification inbox
  (unread count, mark-read, mark-all-read). A separate
  `/dashboard/profile` page holds account info (email, role) and the
  email-notification preference toggle.
- Not built: `saved_items` (bookmarking without tracking — a distinct,
  still-unbuilt feature, [DATABASE.md](DATABASE.md) §2) and any
  document checklist derived from `profiles` attributes (`profiles`
  itself remains unbuilt — [DATABASE.md](DATABASE.md) §17's note).
- Every state is explicit and real, never inert: an unauthenticated
  visit shows a real sign-in prompt (not a blank or fake-populated
  dashboard); loading, error, and empty states are each rendered
  distinctly per section; every tracking/notification action (track,
  pause, resume, remove, mark read) only updates the UI after the
  server confirms it, never optimistically.
- The dashboard never infers or displays a personalization based on data
  the user did not explicitly provide (FR-P2,
  [PRODUCT_REQUIREMENTS.md](PRODUCT_REQUIREMENTS.md) §1.9) — it is a
  read-aggregation view, not a recommendation engine.

## 12. Admin Console (Phase 13, review/approval half only)

A `require_role`-gated composition layer (`app.auth.dependencies`,
[API.md](API.md) §21), realized under `/admin` — narrower than
ROADMAP.md's original Phase 13 sketch (no ingestion-pipeline UI, since
no ingestion pipeline exists; see [DATA_SOURCES.md](DATA_SOURCES.md)
and this phase's ROADMAP.md entry for the scope-difference note):

- **`/admin`** — dashboard: pending-change-record count,
  verification-status distribution across all four domains, recent
  reviewed changes and verifications. Real, data-backed numbers only —
  this phase's explicit "do not introduce fabricated dashboard
  statistics or popularity-based rankings."
- **`/admin/change-records`** — the `ChangeRecord` review queue,
  filterable by status; approve/reject actions only render for a
  `PENDING` record (a decided record shows its outcome, not a
  now-meaningless action).
- **`/admin/verification`** — entities with `verification_status`
  `NEEDS_REVIEW`/`UNVERIFIED`, filterable by entity type; a submission
  form requiring both a decision and an evidence source (the `Select`
  is populated from `/admin/sources`, not a free-text id field — a
  reviewer picks real evidence, never types an unchecked UUID).
- **`/admin/sources`** — read-only source browsing with expandable
  version history; no create/edit action exists (this phase's admin
  console does not fabricate or accept unverified source evidence).
- Client-side RBAC gating (`components/admin/AdminGate.tsx`) is a UX
  convenience only, never the security boundary — every `/api/v1/
  admin/*` call is independently `require_role`-checked server-side
  regardless of what this component renders. A signed-out visitor sees
  a real sign-in prompt; a signed-in `user` sees an explicit "not
  authorized" message (`role="alert"`), never the admin content itself
  and never a silent redirect that could be mistaken for a bug.
  Reused across all four `/admin/*` pages rather than reimplemented
  per page.
- `components/admin/AdminNav.tsx` cross-links the four sections — a
  plain nav, not the `Tabs` component, since these are four separate
  routes, not panels of one page.
- English/Telugu localization via a new `Admin` message namespace,
  following every other namespace's flat-string convention.

## 13. Explicitly Not Built Yet

- Any real domain content page beyond Jobs, Services, Schemes,
  Documents, Eligibility, and Civic AI (representatives/exams/etc.) —
  Jobs (Phase 6, `apps/web/app/[locale]/jobs/`), Services (Phase 7,
  `.../services/`), Schemes (Phase 8, `.../schemes/`), Documents (Phase
  10, `.../documents/`), the Eligibility check (Phase 11,
  `.../eligibility/[entityType]/[slug]/`), and Civic AI (Phase 12,
  `.../ai/`) are the first six; the rest land incrementally against the
  same foundation, reusing the same component set
  (`InformationCard`/`SourceBadge`/`VerificationStatus`/`Breadcrumb`)
  rather than each domain inventing its own card/detail shape —
  Schemes', Documents', Eligibility's, and Civic AI's pages all reuse
  them as-is, with no new shared component extracted for any (each
  domain's shape differed enough — benefits/related services for
  Schemes; supporting-document links/required-by/related-service for
  Documents; a dynamic answer form for Eligibility; a question form with
  citations for Civic AI — that page-level composition, not a shared
  component, is what changed each time). Eligibility reuses one
  design-system component that had sat unused since Phase 4:
  `components/civic/EligibilityStatus`, built ahead of any real engine
  to exist, extended with an optional translated `label` prop (the same
  convention `LastVerified` already used) rather than duplicated. Civic
  AI's page also composes an "Explain this result with Civic AI" button
  directly into the existing `EligibilityForm` (Phase 11) rather than
  building a second eligibility UI — one deterministic result, one
  optional AI-phrased explanation of it, in the same place. Scholarships
  (Phase 9) are not a separate page — they extend
  `.../schemes/page.tsx`'s filter row (one more `<select>`, reusing
  `Pagination`) and `.../schemes/[slug]/page.tsx`'s existing
  `styles.section`/`styles.factItemList` pattern with one more
  conditional section, reusing `LastVerified`'s `label` prop for the
  application-window dates rather than a new date-display component.
- Choice of a client-side data-fetching library (SWR/React Query/etc.)
  beyond the constraints in §5 — every list/detail page (search, jobs,
  services, schemes, documents) still fetches server-side in a Server
  Component via a `lib/*.ts` wrapper following `lib/api.ts`'s original
  health-check pattern. Eligibility (Phase 11) and Civic AI (Phase 12)
  are the two pages with a genuine client-side fetch — `EligibilityForm`/
  `AskCivicAIForm` (`"use client"`) call `POST /api/v1/eligibility/
  evaluate` and `POST /api/v1/ai/ask`/`explain-eligibility` directly via
  `lib/eligibility.ts`/`lib/ai.ts` on submit, since the citizen's own
  input and the resulting answer are interactive, not something to
  server-render — but this remains a plain `fetch` call in a
  `useState`-driven handler, not a new library.
- A component library published as a standalone package — components live
  in `apps/web` until (if ever) a documented reuse need (a second
  consuming app) justifies extraction.
- OpenAPI-generated types in `packages/types` — still hand-written as of
  Phase 10 (`SearchResponse`/`JobDetail`/`ServiceDetail`/`SchemeDetail`/
  `DocumentDetail`/etc.), matching each domain's backend Pydantic
  schemas by hand rather than through generation tooling, which remains
  unbuilt; the OpenAPI-generation step named here is a future
  investment once enough domains exist to justify it.
- Real translations reviewed by a professional Telugu editor (§7) — the
  Schemes namespace's Telugu strings (including the Phase 9 education-
  level/scholarship-detail keys added to the same namespace), the
  Documents namespace's Telugu strings (Phase 10), the Eligibility
  namespace's Telugu strings (Phase 11), and the new CivicAI namespace's
  Telugu strings (Phase 12) are a good-faith machine/manual translation,
  not yet professionally reviewed, same caveat as every other namespace
  so far.

This document now reflects the realized Phase 4 design system/shell and
Phase 5–12's real pages built on it; it is extended, not rewritten, as
further real content pages land.
