# CivicLens — SEO Architecture

This document defines the target SEO architecture. SEO is a named,
first-class requirement (NFR-P2,
[PRODUCT_REQUIREMENTS.md](PRODUCT_REQUIREMENTS.md) §2.2) because most
users will discover CivicLens through search engines looking for a
specific job, scheme, or service — not through direct navigation. This is
the reference for Phase 14 ("SEO + Content Infrastructure" —
[ROADMAP.md](ROADMAP.md)), building on indexable content that lands in
Phases 6–9. **No sitemap, structured data, or metadata implementation
exists yet.**

## 1. URL Structure

Clean, human-readable, locale-prefixed URLs, stable across content
updates (a slug does not change when the underlying fact is corrected —
only the content behind it does):

```
/{locale}/jobs/                              Jobs listing
/{locale}/jobs/{slug}                        Job detail
/{locale}/services/{service-slug}/{state}    Service, state-scoped
/{locale}/schemes/{slug}                     Scheme detail
/{locale}/representatives/{state}/{constituency}   Representative
/{locale}/calculators/{slug}                 Calculator
/{locale}/eligibility/{slug}                 Eligibility check
```

Slugs are generated once at publish time (from the entity's canonical
name plus a disambiguator if needed, e.g., year for a recurring exam) and
are immutable thereafter — a redirect (§4) is used if a slug must ever
change, never a silent URL break. Slugs and routing are owned by the
frontend route structure defined in [FRONTEND.md](FRONTEND.md) §2; this
document defines the URL contract those routes must satisfy for SEO.

## 2. Metadata Strategy

Every public page sets, via Next.js metadata APIs:

- **Title**: entity name + domain + state context (e.g., "APPSC Group 2
  Notification 2026 — CivicLens"), not a generic site-wide title repeated
  across pages.
- **Description**: a factual, non-clickbait summary drawn from the
  entity's actual description/purpose field — never auto-generated filler
  text, consistent with the anti-thin-content policy (§7).
- **Locale metadata** (`hreflang` alternates) linking the `/en/` and
  `/te/` versions of the same page, so search engines serve the correct
  locale to the correct audience rather than treating them as unrelated
  duplicate content.

## 3. Canonical URLs

- Every page declares a canonical URL pointing to its own locale-specific
  path — `/en/jobs/{slug}` canonicalizes to itself, `/te/jobs/{slug}` to
  itself, linked to each other via `hreflang`, not via a single
  cross-locale canonical (which would suppress one locale's indexing).
- Any filtered/paginated view of a listing page (e.g., `/jobs?state=...`)
  canonicalizes to the unfiltered listing unless the filtered view itself
  is judged to have independent search value (e.g., a state-scoped
  services listing, which has its own dedicated route per §1 rather than
  a query-string variant).
- Query parameters that don't change page content for a search engine's
  purposes (sort order, pagination beyond page 1 for thin subsequent
  pages) are excluded from canonical URLs and, where appropriate,
  `noindex`ed.

## 4. Sitemaps

- Generated dynamically (Next.js `sitemap.ts`, per
  [ROADMAP.md](ROADMAP.md) Phase 14 file plan), split by domain
  (`sitemap-jobs.xml`, `sitemap-schemes.xml`, etc.) once volume warrants
  splitting, indexed from a `sitemap-index.xml`.
- Only pages meeting the anti-thin-content policy (§7) are included — a
  page existing in the database does not automatically mean it exists in
  the sitemap.
- A URL is removed from the sitemap (and 410/redirected, not just
  delisted silently) when its underlying entity is soft-deleted
  ([DATABASE.md](DATABASE.md) §5), preventing indexed dead links.
- Sitemap regeneration is tied to the same publish step as ISR
  revalidation ([FRONTEND.md](FRONTEND.md) §3) — a newly published,
  reviewed entity becomes sitemap-visible promptly, not on a slow batch
  cycle.

## 5. Robots.txt Strategy

- Public content domains are fully crawlable by default.
- Explicitly disallowed: `/dashboard/*` (authenticated, personalized, no
  SEO value and a privacy concern if crawled), `/api/*` (not a page
  surface), any internal admin/review routes
  ([DATA_SOURCES.md](DATA_SOURCES.md) §4).
- Search result pages (`/search?...`) are crawlable but `noindex`ed
  (indexable detail pages are the intended landing pages from search
  engines, not CivicLens's own internal search results page) — this
  avoids competing with the detail pages for ranking.

## 6. Structured Data (JSON-LD)

Applied per entity type, using schema.org vocabulary where a real fit
exists — never a mismatched schema type used only for a rich-result
visual effect:

- **Jobs**: `JobPosting` (title, hiringOrganization, datePosted,
  validThrough from `deadlines`, qualifications) — only for fields backed
  by real, sourced data; optional schema.org fields with no CivicLens
  data behind them are omitted, not filled with placeholders.
- **Schemes/Scholarships/Services**: `GovernmentService` where applicable,
  falling back to generic `Article`/`WebPage` structured data plus
  `Organization` (issuing department) when no closer schema.org type fits
  — fit is judged type-by-type at implementation time, not forced.
- **Representatives/Elections**: minimal structured data (`Person`,
  `GovernmentOrganization` roles) — deliberately conservative, since
  overstating structured data here risks implying an endorsement/ranking
  signal, which is prohibited ([DATA_GOVERNANCE.md](DATA_GOVERNANCE.md)
  §5).
- **Breadcrumbs**: `BreadcrumbList` on every detail page (§8).
- All structured data is validated in CI (Phase 14 test requirement,
  [ROADMAP.md](ROADMAP.md)) against schema.org/Google's structured-data
  testing expectations before merge.

## 7. Anti-Thin-Content Policy

This is the binding constraint on all programmatic page generation
(state × service, constituency × representative, etc.):

- A page is indexable **only if** its backing entity's verification
  status is `VERIFIED` or `NEEDS_REVIEW` (shown with its caveat, per
  [DATA_GOVERNANCE.md](DATA_GOVERNANCE.md) §4). `UNVERIFIED` entities
  render (internally reachable, e.g., for review) but are `noindex`ed and
  excluded from the sitemap — a search engine never indexes a fact
  CivicLens itself hasn't confirmed.
- A programmatically-generated page (e.g., a service × state combination)
  must have genuine, non-duplicated content for that specific combination
  — a state-specific process step, document list, or department contact,
  not merely a templated title swap over identical body text. If a
  service is genuinely identical across two states, that is one indexable
  page with two state associations, not two near-duplicate pages created
  to farm URL count.
- A page with no populated required content (e.g., an entity ingested but
  not yet past editorial review, [DATA_SOURCES.md](DATA_SOURCES.md) §4)
  is never published to a public URL at all — thin/empty pages are not
  generated and later cleaned up; they are simply not created in the
  first place.
- This policy is a stated Phase 14 acceptance criterion ("no low-value/
  thin programmatic pages are generated," [ROADMAP.md](ROADMAP.md)) and a
  standing engineering rule ([CLAUDE.md](../CLAUDE.md) rule 19).

## 8. Breadcrumbs & Internal Linking

- Every detail page shows a breadcrumb trail (Home → Domain → \[State\] →
  Entity) matching the URL hierarchy in §1, both visually and as
  `BreadcrumbList` JSON-LD.
- Internal linking is fact-driven, not SEO-engineered filler: a job page
  links to its linked exam(s) and required documents
  ([DATABASE.md](DATABASE.md) §2.3–2.4); a scheme page links to its
  department and related eligibility check; a representative page links
  to their constituency's election history. These links exist because
  [DATABASE.md](DATABASE.md) models the relationship, not because a
  crawl-depth heuristic demands them.
- Listing pages (`/jobs`, `/schemes`, state-scoped listings) serve as the
  primary internal hub pages linking out to detail pages, keeping crawl
  depth shallow from any entry point.

## 9. OpenGraph / Social Metadata

- `og:title`, `og:description` mirror the page metadata (§2); `og:type`
  set appropriately (`article` for content pages); `og:locale` matching
  the active locale with `og:locale:alternate` for the other.
- No auto-generated preview image with fabricated visual "data" (e.g., a
  chart implying statistics not in the source) — a generic branded social
  card is used unless a real, sourced visual asset exists for that entity.

## 10. "Last Verified" Display and SEO Freshness Signals

NFR-T2 ([PRODUCT_REQUIREMENTS.md](PRODUCT_REQUIREMENTS.md) §2.1) requires
every time-sensitive page to visibly show **"Last verified: DATE"**. This
interacts with SEO in two ways CivicLens relies on deliberately:

1. **Freshness signal**: search engines weight genuinely-updated content
   favorably. Because "Last verified" reflects a real
   `verification_records` update (not a cosmetic timestamp bump), page
   `dateModified` structured-data fields and visible freshness are always
   truthful — CivicLens never fakes a freshness signal by touching
   `updated_at` without a real content or verification change.
2. **Trust signal for click-through and dwell time**: a visibly dated,
   sourced page (vs. an undated aggregator page) is expected to perform
   better on user-trust signals search engines increasingly weight
   indirectly (engagement, low pogo-sticking back to results) — this is a
   product-trust outcome ([PRODUCT.md](PRODUCT.md) §7) that also happens
   to serve SEO, not a growth-hack.

An `EXPIRED` entity (per [DATA_GOVERNANCE.md](DATA_GOVERNANCE.md) §4,
e.g., a closed application window) remains indexed with its status
clearly shown, rather than being deleted or hidden — it still answers a
real, common search query ("did the X application close"), and honestly
stating "closed" is genuine user value, not thin content.

## 11. Explicitly Not Built Yet

- Any actual `sitemap.ts`/`robots.ts`, metadata component, or JSON-LD
  template.
- Analytics/Search Console integration and reporting
  ([OBSERVABILITY.md](OBSERVABILITY.md) territory, not this document).
- Any paid search/SEM strategy — out of scope; this document covers
  organic discoverability only.

This document defines the target SEO architecture for Phase 14; it is
finalized against real, live URL patterns once indexable content exists
from Phases 6–9.
