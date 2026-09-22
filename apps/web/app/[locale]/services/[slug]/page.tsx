import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getTranslations, setRequestLocale } from "next-intl/server";
import type { ApplicationChannelType, ServiceDetail } from "@civiclens/types";
import { LastVerified, SourceBadge, VerificationStatus } from "@/components/civic";
import { Container } from "@/components/layout";
import { Breadcrumb } from "@/components/navigation";
import { ExternalLinkIcon } from "@/components/icons";
import type { AppLocale } from "@/i18n/routing";
import { getServiceBySlug } from "@/lib/services";
import { buildLocaleAwareMetadata } from "@/lib/seo";
import styles from "./page.module.css";

interface ServiceDetailPageProps {
  params: Promise<{ locale: string; slug: string }>;
}

export async function generateMetadata({ params }: ServiceDetailPageProps): Promise<Metadata> {
  const { locale, slug } = await params;
  const result = await getServiceBySlug(slug);

  if (!result.reachable || result.data === null) {
    // See apps/web/app/[locale]/jobs/[slug]/page.tsx's identical note:
    // notFound() renders the right content but doesn't reliably set a
    // 404 HTTP status under this project's [locale] routing (a known,
    // disclosed Next.js limitation, docs/ROADMAP.md Phase 4). `noindex`
    // is the mitigation available at this layer.
    return {
      ...buildLocaleAwareMetadata({
        locale: locale as AppLocale,
        path: `/services/${slug}`,
        description: "Service not found.",
      }),
      robots: { index: false, follow: false },
    };
  }

  return buildLocaleAwareMetadata({
    locale: locale as AppLocale,
    path: `/services/${slug}`,
    title: result.data.name,
    description: result.data.short_description ?? result.data.name,
  });
}

// schema.org's GovernmentService type is a real, documented fit for
// this domain (provider/serviceType/areaServed/audience/
// availableChannel all map directly) — chosen per docs/SEO.md §6's
// instruction to judge fit type-by-type rather than force a mismatched
// type for a rich-result effect. Only fields backed by real, sourced
// data are included.
function governmentServiceJsonLd(service: ServiceDetail): Record<string, unknown> {
  const jsonLd: Record<string, unknown> = {
    "@context": "https://schema.org",
    "@type": "GovernmentService",
    name: service.name,
    provider: { "@type": "GovernmentOrganization", name: service.organization.name },
  };
  if (service.short_description) jsonLd.description = service.short_description;
  if (service.service_type) jsonLd.serviceType = service.service_type;
  if (service.state) jsonLd.areaServed = { "@type": "State", name: service.state };
  if (service.target_audience) {
    jsonLd.audience = { "@type": "Audience", audienceType: service.target_audience };
  }
  const channelsWithUrls = service.application_methods.filter((method) => method.url);
  if (channelsWithUrls.length > 0) {
    jsonLd.availableChannel = channelsWithUrls.map((method) => ({
      "@type": "ServiceChannel",
      serviceUrl: method.url,
    }));
  }
  return jsonLd;
}

export default async function ServiceDetailPage({ params }: ServiceDetailPageProps) {
  const { locale, slug } = await params;
  setRequestLocale(locale);

  const [t, result] = await Promise.all([getTranslations("Services"), getServiceBySlug(slug)]);

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

  const service = result.data;

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

  const breadcrumbJsonLd = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: "CivicLens", item: `/${locale}` },
      { "@type": "ListItem", position: 2, name: t("listTitle"), item: `/${locale}/services` },
      { "@type": "ListItem", position: 3, name: service.name },
    ],
  };

  return (
    <Container>
      <div className={styles.page}>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(governmentServiceJsonLd(service)) }}
        />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumbJsonLd) }}
        />

        <Breadcrumb
          items={[
            { label: "CivicLens", href: "/" },
            { label: t("listTitle"), href: "/services" },
            { label: service.name },
          ]}
        />

        <header className={styles.header}>
          <h1 className={styles.title}>{service.name}</h1>
          <p className={styles.subtitle}>
            {service.organization.name}
            {service.department && ` · ${service.department.name}`}
          </p>
          <div className={styles.badges}>
            <VerificationStatus status={service.verification_status} />
            {service.last_verified && (
              <LastVerified date={new Date(service.last_verified)} locale={locale} />
            )}
          </div>
        </header>

        <section className={styles.section} aria-labelledby="overview-heading">
          <h2 id="overview-heading" className={styles.sectionHeading}>
            {t("sectionOverview")}
          </h2>
          <p>{service.description ?? service.short_description}</p>
        </section>

        {service.target_audience && (
          <section className={styles.section} aria-labelledby="audience-heading">
            <h2 id="audience-heading" className={styles.sectionHeading}>
              {t("sectionWhoCanUse")}
            </h2>
            <p>{service.target_audience}</p>
          </section>
        )}

        {service.requirements.length > 0 && (
          <section className={styles.section} aria-labelledby="eligibility-heading">
            <h2 id="eligibility-heading" className={styles.sectionHeading}>
              {t("sectionEligibility")}
            </h2>
            <ul className={styles.factItemList}>
              {service.requirements.map((requirement, index) => (
                <li key={index}>{requirement.description}</li>
              ))}
            </ul>
          </section>
        )}

        {service.required_documents.length > 0 && (
          <section className={styles.section} aria-labelledby="documents-heading">
            <h2 id="documents-heading" className={styles.sectionHeading}>
              {t("sectionRequiredDocuments")}
            </h2>
            <ul className={styles.factItemList}>
              {service.required_documents.map((document, index) => (
                <li key={index}>
                  {document.name}
                  {" — "}
                  <span className={styles.mandatoryTag}>
                    {document.is_mandatory ? t("mandatoryLabel") : t("optionalLabel")}
                  </span>
                  {document.description && `: ${document.description}`}
                </li>
              ))}
            </ul>
          </section>
        )}

        {service.application_methods.length > 0 && (
          <section className={styles.section} aria-labelledby="application-methods-heading">
            <h2 id="application-methods-heading" className={styles.sectionHeading}>
              {t("sectionApplicationMethods")}
            </h2>
            <ul className={styles.factItemList}>
              {service.application_methods.map((method, index) => (
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

        <section className={styles.section} aria-labelledby="fees-heading">
          <h2 id="fees-heading" className={styles.sectionHeading}>
            {t("sectionFees")}
          </h2>
          <p>{service.fee_summary ?? "—"}</p>
        </section>

        <section className={styles.section} aria-labelledby="processing-time-heading">
          <h2 id="processing-time-heading" className={styles.sectionHeading}>
            {t("sectionProcessingTime")}
          </h2>
          <p>{service.processing_time_summary ?? "—"}</p>
        </section>

        <section className={styles.section} aria-labelledby="verification-heading">
          <h2 id="verification-heading" className={styles.sectionHeading}>
            {t("sectionVerification")}
          </h2>
          <div className={styles.badges}>
            <SourceBadge
              kind={service.verification_status === "VERIFIED" ? "verified" : "available"}
            />
            {service.last_verified && (
              <LastVerified date={new Date(service.last_verified)} locale={locale} />
            )}
            <span className={styles.sourceOrganization}>{service.source.organization}</span>
            {service.official_service_url && (
              <a
                href={service.official_service_url}
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
