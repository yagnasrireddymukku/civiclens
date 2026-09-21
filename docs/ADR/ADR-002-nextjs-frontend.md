# ADR-002: Next.js Frontend

## Status
Accepted

## Context
CivicLens's frontend must serve SEO-critical public content (job/scheme/
representative pages, [SEO.md](../SEO.md)) fast on mobile networks, support
i18n (English/Telugu), and provide an authenticated dashboard experience.

## Decision
Use **Next.js (App Router) + TypeScript**. Server-side rendering / static
generation for public, SEO-critical pages (jobs, schemes, representatives,
calculators); client-side interactivity for authenticated/dashboard
features. Styling via a utility-first CSS approach (e.g., Tailwind),
finalized in [FRONTEND.md](../FRONTEND.md) alongside the design system.

## Alternatives Considered
- **Client-only SPA (e.g., plain React + Vite)**: rejected — SEO is a
  named, major requirement ([SEO.md](../SEO.md)); an SPA without SSR/SSG
  would require a separate rendering solution anyway.
- **Server-rendered templates (e.g., Django templates) instead of a
  separate frontend app**: rejected — couples frontend release cadence to
  the Python backend and forecloses a rich, app-like dashboard experience.
- **Remix**: viable alternative with similar SSR strengths; Next.js chosen
  for ecosystem maturity, ISR support (useful for periodically-changing
  civic data pages), and team familiarity assumption.

## Consequences
- Requires a documented API contract with FastAPI (see [API.md](../API.md))
  since frontend and backend are separate deployables.
- Enables Incremental Static Regeneration for high-traffic, infrequently
  changing pages (e.g., a scheme page), reducing backend load.
- TypeScript end-to-end (with generated types from the OpenAPI schema)
  keeps the frontend/backend contract type-safe.
