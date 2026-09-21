import type { Metadata } from "next";
import type { AppLocale } from "@/i18n/routing";

/**
 * Shared metadata foundation — title template, OpenGraph basics, locale
 * alternates. Full sitemap/robots/JSON-LD implementation is
 * docs/ROADMAP.md Phase 14 (docs/SEO.md); this is only the reusable
 * per-page building block that phase will extend, per this phase's SEO
 * foundation scope (metadata, title templates, description, canonical,
 * OpenGraph basics only).
 */

const SITE_NAME = "CivicLens";

export function buildTitle(pageTitle?: string): string {
  return pageTitle ? `${pageTitle} — ${SITE_NAME}` : SITE_NAME;
}

interface PageMetadataInput {
  locale: AppLocale;
  path: string; // locale-relative path, e.g. "/" or "/dev/design-system"
  title?: string;
  description: string;
}

/**
 * Builds canonical + hreflang alternates for a page that exists at the
 * same path under every locale — the standard case per docs/SEO.md §2-3.
 * A page that is genuinely locale-specific (none exist yet) would not
 * use this helper.
 */
export function buildLocaleAwareMetadata({
  locale,
  path,
  title,
  description,
}: PageMetadataInput): Metadata {
  const normalizedPath = path === "/" ? "" : path;

  return {
    title: buildTitle(title),
    description,
    alternates: {
      canonical: `/${locale}${normalizedPath}`,
      languages: {
        en: `/en${normalizedPath}`,
        te: `/te${normalizedPath}`,
      },
    },
    openGraph: {
      title: buildTitle(title),
      description,
      siteName: SITE_NAME,
      locale,
      type: "website",
    },
  };
}
