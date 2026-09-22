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

Realized as five folders under `apps/web/components/`, each with an
`index.ts` barrel:

| Folder | Contains | Examples |
|---|---|---|
| `primitives/` | Generic atoms, no domain knowledge | Button, Input, Textarea, Select, Checkbox, RadioGroup, Switch, Card, Badge, Divider, Skeleton, Spinner |
| `feedback/` | Overlays and status surfaces | Alert, Tooltip, Dialog, Toast (+ `ToastProvider`) |
| `navigation/` | Wayfinding | Tabs, Breadcrumb, Pagination, Dropdown |
| `layout/` | App shell | AppShell, TopNav, Footer, Container, LanguageSwitcher |
| `civic/` | CivicLens-specific, domain-shaped but not domain-data-owning | SourceBadge, VerificationStatus, LastVerified, OfficialSourceCard, EligibilityStatus, DeadlineBadge, SearchResultCard, InformationCard, SearchBar |

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
  navigation, language control, and a user-area placeholder. No
  authentication is implemented (that's ADR-009/Phase 15) — the
  "sign in" control is a disabled button with a tooltip explaining
  accounts aren't available yet, never a functional-looking control that
  does nothing.
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
endpoints for the current user:

- Saved items (`saved_items`), tracked items (`tracking_items`), upcoming
  deadlines (from tracked entities' `deadlines`), and — only where the
  user explicitly provided profile attributes — a document checklist
  (from [ELIGIBILITY_ENGINE.md](ELIGIBILITY_ENGINE.md) §documents linkage).
- The dashboard never infers or displays a personalization based on data
  the user did not explicitly provide (FR-P2,
  [PRODUCT_REQUIREMENTS.md](PRODUCT_REQUIREMENTS.md) §1.9) — it is a
  read-aggregation view, not a recommendation engine.

## 12. Explicitly Not Built Yet

- Any real domain content page beyond Jobs (schemes/services/
  representatives/etc.) — Jobs (Phase 6, `apps/web/app/[locale]/jobs/`)
  is the first; the rest land incrementally against the same foundation.
- Choice of a client-side data-fetching library (SWR/React Query/etc.)
  beyond the constraints in §5 — every real page built so far (search,
  jobs) fetches server-side in a Server Component via a `lib/*.ts`
  wrapper following `lib/api.ts`'s original health-check pattern; no
  page has needed client-side data fetching yet.
- A component library published as a standalone package — components live
  in `apps/web` until (if ever) a documented reuse need (a second
  consuming app) justifies extraction.
- OpenAPI-generated types in `packages/types` — still hand-written as of
  Phase 6 (`SearchResponse`/`JobDetail`/etc.), matching each domain's
  backend Pydantic schemas by hand rather than through generation
  tooling, which remains unbuilt; the OpenAPI-generation step named here
  is a future investment once enough domains exist to justify it.
- Real translations reviewed by a professional Telugu editor (§7).

This document now reflects the realized Phase 4 design system/shell and
Phase 5–6's real pages built on it; it is extended, not rewritten, as
further real content pages land.
