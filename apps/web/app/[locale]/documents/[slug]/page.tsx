import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getTranslations, setRequestLocale } from "next-intl/server";
import type { ApplicationChannelType, DocumentDetail } from "@civiclens/types";
import { LastVerified, SourceBadge, VerificationStatus } from "@/components/civic";
import { Container } from "@/components/layout";
import { Breadcrumb } from "@/components/navigation";
import { ExternalLinkIcon } from "@/components/icons";
import { Link } from "@/i18n/navigation";
import type { AppLocale } from "@/i18n/routing";
import { getDocumentBySlug } from "@/lib/documents";
import { buildLocaleAwareMetadata } from "@/lib/seo";
import styles from "./page.module.css";

interface DocumentDetailPageProps {
  params: Promise<{ locale: string; slug: string }>;
}

export async function generateMetadata({ params }: DocumentDetailPageProps): Promise<Metadata> {
  const { locale, slug } = await params;
  const result = await getDocumentBySlug(slug);

  if (!result.reachable || result.data === null) {
    // See apps/web/app/[locale]/schemes/[slug]/page.tsx's identical
    // note: notFound() renders the right content but doesn't reliably
    // set a 404 HTTP status under this project's [locale] routing (a
    // known, disclosed Next.js limitation, docs/ROADMAP.md Phase 4).
    // `noindex` is the mitigation available at this layer — preserved
    // here rather than reinvented.
    return {
      ...buildLocaleAwareMetadata({
        locale: locale as AppLocale,
        path: `/documents/${slug}`,
        description: "Document not found.",
      }),
      robots: { index: false, follow: false },
    };
  }

  return buildLocaleAwareMetadata({
    locale: locale as AppLocale,
    path: `/documents/${slug}`,
    title: result.data.name,
    description: result.data.short_description ?? result.data.name,
  });
}

// schema.org's own documentation of GovernmentService lists examples
// ("food stamps, veterans benefits, license plates, etc.") that
// explicitly include obtaining an official document/identity record —
// so, like Services and Schemes, this is a genuine fit judged by real
// documented properties, not a name that merely sounds plausible
// (docs/SEO.md §6). A `GovernmentPermit` type was considered for
// PERMIT/LICENSE/REGISTRATION document types specifically and rejected:
// branching structured-data type by `document_type` for a marginal SEO
// gain added complexity this phase's data model doesn't otherwise
// need — `GovernmentService` already covers every document type
// honestly (docs/SEO.md §16).
function governmentServiceJsonLd(document: DocumentDetail): Record<string, unknown> {
  const jsonLd: Record<string, unknown> = {
    "@context": "https://schema.org",
    "@type": "GovernmentService",
    name: document.name,
    provider: { "@type": "GovernmentOrganization", name: document.organization.name },
    serviceType: document.document_type,
  };
  if (document.short_description) jsonLd.description = document.short_description;
  if (document.state) jsonLd.areaServed = { "@type": "State", name: document.state };
  const channelsWithUrls = document.application_methods.filter((method) => method.url);
  if (channelsWithUrls.length > 0) {
    jsonLd.availableChannel = channelsWithUrls.map((method) => ({
      "@type": "ServiceChannel",
      serviceUrl: method.url,
    }));
  }
  return jsonLd;
}

export default async function DocumentDetailPage({ params }: DocumentDetailPageProps) {
  const { locale, slug } = await params;
  setRequestLocale(locale);

  const [t, result] = await Promise.all([getTranslations("Documents"), getDocumentBySlug(slug)]);

  if (!result.reachable) {
    return (
      <Container>
        <div className={styles.page}>
          <p className={styles.errorText}>{result.error}</p>
        </div>
      </Container>
    );
  }
  if (result.data === null) {
    notFound();
  }

  const document = result.data;

  const channelLabels: Record<ApplicationChannelType, string> = {
    ONLINE: t("channelOnline"),
    OFFLINE: t("channelOffline"),
    MOBILE_APP: t("channelMobileApp"),
    MEESEVA: t("channelMeeseva"),
    DEPARTMENT_PORTAL: t("channelDepartmentPortal"),
    SERVICE_CENTER: t("channelServiceCenter"),
    IN_PERSON: t("channelInPerson"),
    OTHER: t("channelOther"),
  };

  const requiredByLabels = {
    service: t("requiredByService"),
    scheme: t("requiredByScheme"),
  } as const;

  const breadcrumbJsonLd = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: "CivicLens", item: `/${locale}` },
      { "@type": "ListItem", position: 2, name: t("listTitle"), item: `/${locale}/documents` },
      { "@type": "ListItem", position: 3, name: document.name },
    ],
  };

  return (
    <Container>
      <div className={styles.page}>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(governmentServiceJsonLd(document)) }}
        />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumbJsonLd) }}
        />

        <Breadcrumb
          items={[
            { label: "CivicLens", href: "/" },
            { label: t("listTitle"), href: "/documents" },
            { label: document.name },
          ]}
        />

        <header className={styles.header}>
          <h1 className={styles.title}>{document.name}</h1>
          <p className={styles.subtitle}>
            {document.organization.name}
            {document.department && ` · ${document.department.name}`}
          </p>
          <div className={styles.badges}>
            <VerificationStatus status={document.verification_status} />
            {document.last_verified && (
              <LastVerified date={new Date(document.last_verified)} locale={locale} />
            )}
          </div>
        </header>

        <section className={styles.section} aria-labelledby="overview-heading">
          <h2 id="overview-heading" className={styles.sectionHeading}>
            {t("sectionOverview")}
          </h2>
          <p>{document.description ?? document.short_description}</p>
        </section>

        {document.purpose && (
          <section className={styles.section} aria-labelledby="purpose-heading">
            <h2 id="purpose-heading" className={styles.sectionHeading}>
              {t("sectionPurpose")}
            </h2>
            <p>{document.purpose}</p>
          </section>
        )}

        {document.requirements.length > 0 && (
          <section className={styles.section} aria-labelledby="requirements-heading">
            <h2 id="requirements-heading" className={styles.sectionHeading}>
              {t("sectionRequirements")}
            </h2>
            <ul className={styles.factItemList}>
              {document.requirements.map((requirement, index) => (
                <li key={index}>{requirement.description}</li>
              ))}
            </ul>
          </section>
        )}

        {document.supporting_documents.length > 0 && (
          <section className={styles.section} aria-labelledby="supporting-documents-heading">
            <h2 id="supporting-documents-heading" className={styles.sectionHeading}>
              {t("sectionSupportingDocuments")}
            </h2>
            <ul className={styles.factItemList}>
              {document.supporting_documents.map((supporting, index) => (
                <li key={index}>
                  {supporting.civic_document ? (
                    <Link href={`/documents/${supporting.civic_document.slug}`}>
                      {supporting.name}
                    </Link>
                  ) : (
                    supporting.name
                  )}
                  {" — "}
                  <span className={styles.mandatoryTag}>
                    {supporting.is_mandatory ? t("mandatoryLabel") : t("optionalLabel")}
                  </span>
                  {supporting.description && `: ${supporting.description}`}
                </li>
              ))}
            </ul>
          </section>
        )}

        {document.application_methods.length > 0 && (
          <section className={styles.section} aria-labelledby="application-methods-heading">
            <h2 id="application-methods-heading" className={styles.sectionHeading}>
              {t("sectionApplicationMethods")}
            </h2>
            <ul className={styles.factItemList}>
              {document.application_methods.map((method, index) => (
                <li key={index}>
                  {channelLabels[method.channel_type]}
                  {method.instructions && ` — ${method.instructions}`}
                  {method.url && (
                    <>
                      {" "}
                      <a
                        href={method.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className={styles.officialLink}
                      >
                        {t("sectionOfficialApplication")}
                        <ExternalLinkIcon className={styles.linkIcon} />
                      </a>
                    </>
                  )}
                </li>
              ))}
            </ul>
          </section>
        )}

        {(document.fee_summary || document.processing_time_summary) && (
          <section className={styles.section} aria-labelledby="fees-processing-heading">
            <h2 id="fees-processing-heading" className={styles.sectionHeading}>
              {t("sectionFeesAndProcessing")}
            </h2>
            <ul className={styles.factItemList}>
              {document.fee_summary && (
                <li>
                  {t("sectionFees")}: {document.fee_summary}
                </li>
              )}
              {document.processing_time_summary && (
                <li>
                  {t("sectionProcessingTime")}: {document.processing_time_summary}
                </li>
              )}
            </ul>
          </section>
        )}

        {(document.validity_summary || document.renewal_summary) && (
          <section className={styles.section} aria-labelledby="validity-heading">
            <h2 id="validity-heading" className={styles.sectionHeading}>
              {t("sectionValidity")}
            </h2>
            <ul className={styles.factItemList}>
              {document.validity_summary && <li>{document.validity_summary}</li>}
              {document.renewal_summary && <li>{document.renewal_summary}</li>}
            </ul>
          </section>
        )}

        {document.service && (
          <section className={styles.section} aria-labelledby="related-service-heading">
            <h2 id="related-service-heading" className={styles.sectionHeading}>
              {t("sectionRelatedService")}
            </h2>
            <p>{document.service.name}</p>
          </section>
        )}

        {document.required_by.length > 0 && (
          <section className={styles.section} aria-labelledby="required-by-heading">
            <h2 id="required-by-heading" className={styles.sectionHeading}>
              {t("sectionRequiredBy")}
            </h2>
            <ul className={styles.factItemList}>
              {document.required_by.map((entry, index) => (
                <li key={index}>
                  {entry.name} ({requiredByLabels[entry.entity_type]})
                </li>
              ))}
            </ul>
          </section>
        )}

        <section className={styles.section} aria-labelledby="verification-heading">
          <h2 id="verification-heading" className={styles.sectionHeading}>
            {t("sectionVerification")}
          </h2>
          <div className={styles.badges}>
            <SourceBadge
              kind={document.verification_status === "VERIFIED" ? "verified" : "available"}
            />
            {document.last_verified && (
              <LastVerified date={new Date(document.last_verified)} locale={locale} />
            )}
            <span className={styles.sourceOrganization}>{document.source.organization}</span>
            {document.official_document_url && (
              <a
                href={document.official_document_url}
                target="_blank"
                rel="noopener noreferrer"
                className={styles.officialLink}
              >
                {t("sectionOfficialSource")}
                <ExternalLinkIcon className={styles.linkIcon} />
              </a>
            )}
          </div>
        </section>
      </div>
    </Container>
  );
}
